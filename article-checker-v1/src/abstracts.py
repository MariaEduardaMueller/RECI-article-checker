"""RESUMOS — itens 24 a 28 e 113 (versões em português, inglês e espanhol)."""
import re

from common import Ctx, fmt_list, is_simple, n_words, res

DESC_RX = re.compile(r"^\s*(Descritores|Keywords|Key\s+words|Palabras[-\s]+clave|Descriptores|Unitermos|Palavras[-\s]chave)\s*:", re.IGNORECASE)
VERSIONS = {
    "RESUMO": ("Justificativa e Objetivos:", "Métodos:", "Resultados:", "Conclusão:"),
    "ABSTRACT": ("Background and Objectives:", "Methods:", "Results:", "Conclusion:"),
    "RESUMEN": ("Justificación y Objetivos:", "Métodos:", "Resultados:", "Conclusión:"),
}
ITEM_OF = {"RESUMO": 25, "ABSTRACT": 26, "RESUMEN": 27}
DESC_OF = {
    25: "RESUMO – Justificativa e Objetivos, Métodos, Resultados e Conclusão (versão portuguesa)",
    26: "ABSTRACT – Background and Objectives, Methods, Results e Conclusion (versão inglesa)",
    27: "RESUMEN – Justificación y Objetivos, Métodos, Resultados e Conclusión (versão espanhola)",
}


def abstract_content(ctx: Ctx, key):
    """Parágrafos do resumo, sem o rótulo de descritores."""
    return [p for p in ctx.sections.get(key) if not DESC_RX.match(p.stripped)]


def item_24(ctx: Ctx):
    desc = "Conciso, limite máximo de 250 palavras, em parágrafo único, com espaçamento simples entre as linhas"
    exact = ctx.doc.exact
    problems, notes = [], []
    for key in VERSIONS:
        paras = abstract_content(ctx, key)
        if not paras:
            problems.append(f"{key} não encontrado")
            continue
        words = sum(n_words(p.stripped) for p in paras)
        if len(paras) > 1:
            problems.append(f"{key}: deve ter parágrafo único, encontrados {len(paras)}" + ("" if exact else " (PDF: contagem estimada)"))
        if words > 250:
            problems.append(f"{key}: {words} palavras (máximo 250)")
        bad_ls = [p for p in paras if is_simple(p, exact) is False]
        if bad_ls:
            problems.append(f"{key}: espaçamento entre linhas {bad_ls[0].line_spacing:g} (esperado simples)")
        notes.append(f"{key} {words} palavras")
    if problems:
        return res(24, desc, "NA", "; ".join(problems))
    return res(24, desc, "A", "Resumos corretos (" + ", ".join(notes) + "; parágrafo único; espaçamento simples)")


def check_structure(ctx: Ctx, key):
    """Devolve lista de problemas (vazia = ok) para a estrutura de um resumo."""
    paras = abstract_content(ctx, key)
    if not paras:
        return [f"{key} não encontrado"]
    problems, last_pos = [], -1
    full = "\n".join(p.text for p in paras)
    for label in VERSIONS[key]:
        rx = re.compile(re.escape(label), re.IGNORECASE)
        found = False
        for p in paras:
            m = rx.search(p.text)
            if not m:
                continue
            found = True
            if not m.group(0)[:1].isupper():
                problems.append(f"'{label}' deve iniciar com letra maiúscula")
            runs = p.runs_in(m.start(), m.end())
            if not runs or not all(r.bold for r in runs):
                problems.append(f"'{label}' não está em negrito")
            pos = rx.search(full).start()
            if pos < last_pos:
                problems.append(f"'{label}' fora de ordem")
            last_pos = max(last_pos, pos)
            break
        if not found:
            m2 = re.search(re.escape(label.rstrip(":")), full, re.IGNORECASE)
            problems.append(f"'{label}' sem dois-pontos" if m2 else f"'{label}' não encontrado")
    return problems


def _item_struct(ctx: Ctx, key):
    n = ITEM_OF[key]
    problems = check_structure(ctx, key)
    return res(n, DESC_OF[n], "NA" if problems else "A", "; ".join(problems) if problems else f"{key} estruturado corretamente")


def item_25(ctx: Ctx): return _item_struct(ctx, "RESUMO")
def item_26(ctx: Ctx): return _item_struct(ctx, "ABSTRACT")
def item_27(ctx: Ctx): return _item_struct(ctx, "RESUMEN")


def item_28(ctx: Ctx):
    desc = ("Estruturado e separado nas seções: Justificativa e Objetivos, Métodos, Resultados, Conclusão "
            "(todos em negrito, somente a primeira letra em maiúsculo e seguido por dois pontos)")
    rs = [item_25(ctx), item_26(ctx), item_27(ctx)]
    ok = [r["item"] for r in rs if r["status"] == "A"]
    if len(ok) == 3:
        return res(28, desc, "A", "Os três resumos estão estruturados corretamente")
    if ok:
        return res(28, desc, "AP", f"{len(ok)}/3 resumos estruturados corretamente (itens {ok})")
    return res(28, desc, "NA", "Nenhum dos resumos está estruturado corretamente")


def item_113(ctx: Ctx):
    desc = "Resumos abaixo dos títulos, com versões nos três idiomas"
    S = ctx.sections
    missing = [k for k in VERSIONS if not S.has(k)]
    if missing:
        return res(113, desc, "NA", f"Resumo(s) ausente(s): {', '.join(missing)}")
    order = [k for k in S.order if k in VERSIONS or k in ("INTRODUCTION",)]
    expected = ["RESUMO", "ABSTRACT", "RESUMEN", "INTRODUCTION"]
    if order[:4] != expected:
        return res(113, desc, "AP", "Ordem encontrada: " + " > ".join(order) + " (esperado: RESUMO > ABSTRACT > RESUMEN > INTRODUÇÃO)")
    if not S.content.get("FRONT") or not any(p.stripped for p in S.content["FRONT"]):
        return res(113, desc, "NA", "Títulos não encontrados antes dos resumos")
    return res(113, desc, "A", "Resumos em português, inglês e espanhol, abaixo dos títulos")
