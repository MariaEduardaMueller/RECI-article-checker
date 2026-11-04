"""Tipos e utilitários compartilhados por todas as verificações."""
from __future__ import annotations

import datetime
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from document_model import Document

# Legenda do Checklist da RECI: azul = atende | verde = parcialmente | amarelo = não atende
STATUS_LABEL = {
    "A": "Atende",
    "AP": "Atende parcialmente",
    "NA": "Não atende",
    "NSA": "Não se aplica",
    "-": "Não verificado",
}

#qwen2.5:7b-instruct
#qwen2.5:1.5b
DEFAULT_MODEL = "qwen2.5:1.5b"
RECENT_YEARS = 5                    # "últimos 5 anos"


def res(item, description: str, status: str, comments: str = "") -> dict:
    return {"item": item, "description": description, "status": status, "comments": comments}


def recent_cutoff() -> int:
    return datetime.date.today().year - RECENT_YEARS


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def n_words(text: str) -> int:
    return len(text.split())


def norm_font(name: str | None) -> str:
    return re.sub(r"[^a-z]", "", (name or "").lower())


# Fontes métricamente compatíveis com a Times New Roman (comuns em PDFs gerados no Linux/LibreOffice)
_TNR_ALIASES = ("timesnewroman", "liberationserif", "tinos", "nimbusroman", "timesroman", "times")


def is_times(name: str | None) -> bool:
    n = norm_font(name)
    return any(n.startswith(a) or a in n for a in _TNR_ALIASES)


def is_simple(p, exact: bool = True) -> bool | None:
    """Espaçamento entre linhas 'simples'. No .docx o valor é exato; no PDF é estimado."""
    v = p.line_spacing
    if v is None:
        return None
    return abs(v - 1.0) <= 0.03 if exact else v <= 1.2


def is_one_half(p, exact: bool = True) -> bool | None:
    v = p.line_spacing
    if v is None:
        return None
    return abs(v - 1.5) <= 0.03 if exact else 1.35 <= v <= 1.7


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
    """Tamanhos de fonte dentro da tolerância (PDF reporta 10,1pt para 10pt)."""
    return all(abs(x - target) <= tol for x in sizes)


def fmt_list(items, limit: int = 5, sep: str = "; ") -> str:
    items = list(items)
    s = sep.join(str(i) for i in items[:limit])
    if len(items) > limit:
        s += f" (e mais {len(items) - limit})"
    return s


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
