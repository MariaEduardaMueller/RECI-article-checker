"""Divisão do manuscrito em seções (por parágrafos; funciona para .docx e .pdf)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from document_model import Document, Para

HEADINGS = {
    "RESUMO": r"resumo",
    "ABSTRACT": r"abstract",
    "RESUMEN": r"resumen",
    "INTRODUCTION": r"introdu[cç][aã]o|introduction|introducci[oó]n",
    "METHODS": r"m[eé]todos?|methods?|metodolog[ií]a",
    "RESULTS": r"resultados?|results?",
    "DISCUSSION": r"discuss[aã]o|discussion|discusi[oó]n",
    "CONCLUSION": r"conclus[aã]o|conclusion|conclusi[oó]n|considera[cç][oõ]es\s+finais",
    "ACKNOWLEDGMENTS": r"agradecimentos?|acknowledg(?:e)?ments?",
    "REFERENCES": r"refer[eê]ncias?(?:\s+bibliogr[aá]ficas)?|references?|bibliografia",
    "CONTRIBUTIONS": r"contribui[cç][oõ]es(?:\s+dos\s+autores)?|contributions",
}

# Seções de corpo do artigo (da Introdução à Discussão)
BODY_KEYS = ("INTRODUCTION", "METHODS", "RESULTS", "DISCUSSION")
SECTION_PT = {"INTRODUCTION": "Introdução", "METHODS": "Métodos", "RESULTS": "Resultados",
              "DISCUSSION": "Discussão", "REFERENCES": "Referências", "CONCLUSION": "Conclusão",
              "ACKNOWLEDGMENTS": "Agradecimentos"}


INLINE_ABSTRACT = re.compile(r"^\s*(Resumo|Abstract|Resumen)\s*:\s*\S")
INLINE_KEY = {"resumo": "RESUMO", "abstract": "ABSTRACT", "resumen": "RESUMEN"}


def heading_key(p: Para) -> str | None:
    t = p.stripped
    if not t or p.in_table or len(t) > 45:
        return None
    t = re.sub(r"^[\d.\s)]+", "", t).strip().rstrip(":.").strip()
    for key, rx in HEADINGS.items():
        if re.fullmatch(rx, t, re.IGNORECASE):
            return key
    return None


@dataclass
class Sections:
    content: dict = field(default_factory=dict)     # chave -> [Para]
    heading: dict = field(default_factory=dict)     # chave -> Para do título
    order: list = field(default_factory=list)

    def get(self, key) -> list[Para]:
        return [p for p in self.content.get(key, []) if p.stripped]

    def has(self, key) -> bool:
        return key in self.heading

    def text(self, key) -> str:
        return "\n".join(p.stripped for p in self.get(key))

    def words(self, key) -> int:
        return len(self.text(key).split())


def split_sections(doc: Document) -> Sections:
    s = Sections()
    current = "FRONT"
    s.content[current] = []
    s.order.append(current)
    for p in doc.body:
        inline = INLINE_ABSTRACT.match(p.stripped)
        if inline and not s.has(INLINE_KEY[inline.group(1).lower()]):
            current = INLINE_KEY[inline.group(1).lower()]
            s.heading[current] = p
            s.content[current] = [p]                  # o conteúdo começa no mesmo parágrafo do rótulo
            s.order.append(current)
            continue
        key = heading_key(p)
        if key and key not in s.heading:
            current = key
            s.heading[key] = p
            s.content[key] = []
            s.order.append(key)
            continue
        if key:                                   # título repetido (ex.: "Referências" em outro ponto)
            current = key + "#" + str(len(s.order))
            s.content[current] = []
            continue
        s.content[current].append(p)
    return s
