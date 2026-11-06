"""Tipos e utilitários compartilhados por todas as verificações."""
from __future__ import annotations

import datetime
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from document_model import Document, Para

# Legenda do Checklist da RECI: azul = atende | verde = parcialmente | amarelo = não atende | cinza = não se aplica
STATUS_LABEL = {
    "A": "Atende",
    "AP": "Atende parcialmente",
    "NA": "Não atende",
    "NSA": "Não se aplica",
    "-": "Verificar manualmente",
    "SKIP": "Fora do escopo",
}

# qwen2.5:7b-instruct (mais preciso)  |  qwen2.5:1.5b (mais leve)
DEFAULT_MODEL = "qwen2.5:1.5b"
RECENT_YEARS = 5                    # "últimos 5 anos"
MAX_ABSTRACT_WORDS = 256            # alteração da RECI em relação ao Checklist-modelo (250)


def res(item, description: str, status: str, comments: str = "", notes: list | None = None) -> dict:
    """Resultado de um item. `notes` = comentários a ancorar no texto do manuscrito (ver note())."""
    return {"item": item, "description": description, "status": status, "comments": comments, "notes": notes or []}


def note(p: Para | None, text: str, start: int | None = None, end: int | None = None) -> dict:
    """Comentário para a cópia comentada: parágrafo `p`, trecho [start, end) (None = parágrafo inteiro)."""
    return {"para": None if p is None else p.index, "start": start, "end": end, "text": text}


def recent_cutoff() -> int:
    return datetime.date.today().year - RECENT_YEARS


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def n_words(text: str) -> int:
    return len(text.split())


def norm_font(name: str | None) -> str:
    return re.sub(r"[^a-z]", "", (name or "").lower())


_TNR_ALIASES = ("timesnewroman", "liberationserif", "tinos", "nimbusroman", "timesroman", "times")


def is_times(name: str | None) -> bool:
    n = norm_font(name)
    return any(n.startswith(a) or a in n for a in _TNR_ALIASES)


def is_simple(p, exact: bool = True) -> bool | None:
    """Espaçamento entre linhas 'simples' (1,0)."""
    v = p.line_spacing
    if v is None:
        return None
    return abs(v - 1.0) <= 0.03


def is_one_half(p, exact: bool = True) -> bool | None:
    v = p.line_spacing
    if v is None:
        return None
    return abs(v - 1.5) <= 0.03


UF_NAMES = {
    "Acre", "Alagoas", "Amapá", "Amazonas", "Bahia", "Ceará", "Distrito Federal", "Espírito Santo", "Goiás",
    "Maranhão", "Mato Grosso", "Mato Grosso do Sul", "Minas Gerais", "Pará", "Paraíba", "Paraná", "Pernambuco",
    "Piauí", "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul", "Rondônia", "Roraima",
    "Santa Catarina", "São Paulo", "Sergipe", "Tocantins",
}
UF_SIGLAS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE",
             "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}


def has_uf(text: str) -> bool:
    if any(re.search(rf"(?<!\w){re.escape(u)}(?!\w)", text) for u in UF_NAMES):
        return True
    return bool(re.search(r"(?:,|-|/|\()\s*(?:" + "|".join(UF_SIGLAS) + r")\b", text))


def sizes_ok(sizes, target: float, tol: float = 0.35) -> bool:
    return all(abs(x - target) <= tol for x in sizes)


def fmt_list(items, limit: int = 5, sep: str = "; ") -> str:
    items = list(items)
    s = sep.join(str(i) for i in items[:limit])
    if len(items) > limit:
        s += f" (e mais {len(items) - limit})"
    return s


SECTION_LABEL = {
    "FRONT": "Título/cabeçalho", "RESUMO": "RESUMO", "ABSTRACT": "ABSTRACT", "RESUMEN": "RESUMEN",
    "INTRODUCTION": "Introdução", "METHODS": "Métodos", "RESULTS": "Resultados", "DISCUSSION": "Discussão",
    "CONCLUSION": "Conclusão", "ACKNOWLEDGMENTS": "Agradecimentos", "REFERENCES": "Referências",
    "CONTRIBUTIONS": "Contribuição dos autores",
}


def _ordinal(n: int) -> str:
    return f"{n}º parágrafo"


@dataclass
class Ctx:
    """Contexto compartilhado: documentos carregados + opções + cache."""
    doc: Document
    cover: Document | None = None
    attachments_dir: Path | None = None
    use_llm: bool = True
    llm_model: str = DEFAULT_MODEL
    cache: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.doc.text

    def memo(self, key, fn):
        if key not in self.cache:
            self.cache[key] = fn()
        return self.cache[key]

    @property
    def sections(self):
        from structure import split_sections
        return self.memo("sections", lambda: split_sections(self.doc))

    # ---- localização (seção + nº do parágrafo) usada nos comentários do Checklist ------------------
    def _locator(self):
        def build():
            m = {}
            for key, paras in self.sections.content.items():
                base = key.split("#")[0]
                k = 0
                for p in paras:
                    if p.stripped:
                        k += 1
                        m[p.index] = (SECTION_LABEL.get(base, base), k)
            for h in self.sections.heading.values():
                m.setdefault(h.index, (None, 0))
            return m
        return self.memo("locator", build)

    def where(self, p: Para | None, snippet: bool = False, n: int = 40) -> str:
        if p is None:
            return "documento"
        if p.in_table:
            s = f"dentro da Tabela {(p.table_index or 0) + 1}"
        else:
            label, k = self._locator().get(p.index, (None, 0))
            if label is None:
                heading = next((kk for kk, h in self.sections.heading.items() if h.index == p.index), None)
                s = f"título da seção {SECTION_LABEL.get(heading, heading)}" if heading else f"parágrafo {p.index + 1} do documento"
            else:
                s = f"{label}, {_ordinal(k)}"
        if snippet and p.stripped:
            t = " ".join(p.stripped.split())
            s += f" (“{t[:n]}{'…' if len(t) > n else ''}”)"
        return s
