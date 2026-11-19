"""RESUMOS — conciso (máx. 256 palavras), estrutura por idioma, ausência de citações (versões PT, EN e ES)."""
import re

from common import (ABSTRACT_OF_LANG, LANG_PT, MAX_ABSTRACT_WORDS, REQUIRE_LEFT_ALIGN_ABSTRACTS, Ctx, fmt_list, is_simple, ls_label,
                    n_words, note, res, work_lang)

DESC_RX = re.compile(r"^\s*(Descritores|Keywords|Key\s+words|Palabras[-\s]+clave|Descriptores|Unitermos|Palavras[-\s]chave)\s*:", re.IGNORECASE)
VERSIONS = {
    "RESUMO": ("Justificativa e Objetivos:", "Métodos:", "Resultados:", "Conclusão:"),
    "ABSTRACT": ("Background and Objectives:", "Methods:", "Results:", "Conclusion:"),
    "RESUMEN": ("Justificación y Objetivos:", "Métodos:", "Resultados:", "Conclusión:"),
}
ID_OF = {"RESUMO": "re.resumo", "ABSTRACT": "re.abstract", "RESUMEN": "re.resumen"}


def abstract_content(ctx: Ctx, key):
    """Parágrafos do resumo, sem o rótulo de descritores."""
    return [p for p in ctx.sections.get(key) if not DESC_RX.match(p.stripped)]


def item_re_abaixo(ctx: Ctx):
    desc = "Resumos abaixo dos títulos, com versões nos três idiomas"
    S = ctx.sections
    missing = [k for k in VERSIONS if not S.has(k)]
    if missing:
        return res("re.abaixo", desc, "NA", f"Resumo(s) ausente(s): {', '.join(missing)}. Inclua as três versões (RESUMO, ABSTRACT, RESUMEN) logo abaixo dos títulos.",
                   [note(S.heading[k], f"Falta a versão {', '.join(missing)} do resumo.") for k in VERSIONS if k in S.heading][:1] or [note(None, f"Resumo(s) ausente(s): {', '.join(missing)}.")])
    order = [k for k in S.order if k in VERSIONS or k == "INTRODUCTION"]
    first = ABSTRACT_OF_LANG[work_lang(ctx)]            # o 1º resumo deve estar no idioma do artigo
    if order[:3] and order[0] != first or order[3:4] != ["INTRODUCTION"]:
        first_h = S.heading[order[0]] if order and order[0] in S.heading else S.heading["RESUMO"]
        return res("re.abaixo", desc, "AP", f"Ordem encontrada: {' > '.join(order)}. O artigo está em {LANG_PT[work_lang(ctx)]}: o primeiro resumo deve ser o {first}, seguido dos outros dois, antes da Introdução.",
                   [note(first_h, f"O artigo está em {LANG_PT[work_lang(ctx)]}: apresente primeiro o {first}, depois as outras duas versões, antes da Introdução.")])
    if not any(p.stripped for p in S.content.get("FRONT", [])):
        return res("re.abaixo", desc, "NA", "Títulos não encontrados antes dos resumos")
    return res("re.abaixo", desc, "A", "Resumos em português, inglês e espanhol, abaixo dos títulos")


def item_re_conciso(ctx: Ctx):
    desc = f"Conciso, limite máximo de {MAX_ABSTRACT_WORDS} palavras, em parágrafo único, com espaçamento simples entre as linhas e alinhado à esquerda"
    problems, notes, ok, obs = [], [], [], []
    for key in VERSIONS:
        paras = abstract_content(ctx, key)
        if not paras:
            problems.append(f"{key} não encontrado")
            continue
        words = sum(n_words(p.stripped) for p in paras)
        if len(paras) > 1:
            problems.append(f"{key}: deve ter parágrafo único, encontrados {len(paras)} ({ctx.where(paras[1])})")
            notes.append(note(paras[1], f"O resumo deve ter parágrafo único: una este parágrafo ao anterior ({len(paras)} parágrafos encontrados)."))
        if words > MAX_ABSTRACT_WORDS:
            problems.append(f"{key}: {words} palavras (máximo {MAX_ABSTRACT_WORDS}); reduzir {words - MAX_ABSTRACT_WORDS} palavra(s)")
            notes.append(note(paras[0], f"Resumo com {words} palavras; o limite é {MAX_ABSTRACT_WORDS}. Reduza {words - MAX_ABSTRACT_WORDS} palavra(s)."))
        bad = [p for p in paras if is_simple(p) is False]
        if bad:
            problems.append(f"{key}: espaçamento entre linhas {ls_label(bad[0])} (esperado simples) em {ctx.where(bad[0])}")
            notes.append(note(bad[0], "Resumo deve ter espaçamento simples entre as linhas."))
        heads = [h for h in [ctx.sections.heading.get(key)] if h is not None]
        misaligned = [p for p in heads + paras if p.align in ("justify", "center", "right")]
        if misaligned:
            names = {"justify": "justificado", "center": "centralizado", "right": "à direita"}
            msg = f"{key}: {names[misaligned[0].align]} (a RECI pede alinhamento à esquerda; formatação final a confirmar)"
            if REQUIRE_LEFT_ALIGN_ABSTRACTS:
                problems.append(msg)
                notes += [note(p, f"O {key} deve estar alinhado à esquerda (atualmente {names[p.align]}).") for p in misaligned[:3]]
            else:
                obs.append(msg)                           # só observação: não altera o status
        ok.append(f"{key} {words} palavras")
    if problems:
        return res("re.conciso", desc, "NA", "; ".join(problems) + ((" | Observação: " + "; ".join(obs)) if obs else ""), notes)
    return res("re.conciso", desc, "A", "Resumos corretos (" + ", ".join(ok) + "; parágrafo único; espaçamento simples)" + ((" | Observação: " + "; ".join(obs)) if obs else ""))


def check_structure(ctx: Ctx, key):
    """Devolve [(mensagem, parágrafo)] para a estrutura de um resumo (vazio = ok)."""
    paras = abstract_content(ctx, key)
    if not paras:
        return [(f"{key} não encontrado", None)]
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
                problems.append((f"'{label}' deve iniciar com letra maiúscula", (p, m.start(), m.end())))
            runs = p.runs_in(m.start(), m.end())
            if not runs or not all(r.bold for r in runs):
                problems.append((f"'{label}' não está em negrito", (p, m.start(), m.end())))
            pos = rx.search(full).start()
            if pos < last_pos:
                problems.append((f"'{label}' fora de ordem", (p, m.start(), m.end())))
            last_pos = max(last_pos, pos)
            break
        if not found:
            m2 = re.search(re.escape(label.rstrip(":")), full, re.IGNORECASE)
            if m2:
                p0 = next(p for p in paras if re.search(re.escape(label.rstrip(":")), p.text, re.IGNORECASE))
                mm = re.search(re.escape(label.rstrip(":")), p0.text, re.IGNORECASE)
                problems.append((f"'{label}' sem dois-pontos", (p0, mm.start(), mm.end())))
            else:
                problems.append((f"'{label}' não encontrado", (paras[0], None, None)))
    return problems


def _item_struct(ctx: Ctx, key):
    iid = ID_OF[key]
    desc = f"{key} — " + ", ".join(l.rstrip(":") for l in VERSIONS[key]) + " (todos em negrito e seguidos de dois pontos)"
    probs = check_structure(ctx, key)
    if not probs:
        return res(iid, desc, "A", f"{key} estruturado corretamente")
    notes = [note(t[0], f"{msg}.", t[1], t[2]) for msg, t in probs if t]
    h = ctx.sections.heading.get(key)
    where = "; ".join(f"{m} ({ctx.where(t[0])})" if t else m for m, t in probs)
    return res(iid, desc, "AP" if len(probs) < 3 and all(t for _, t in probs) else "NA", where, notes)


def item_re_resumo(ctx: Ctx): return _item_struct(ctx, "RESUMO")
def item_re_abstract(ctx: Ctx): return _item_struct(ctx, "ABSTRACT")
def item_re_resumen(ctx: Ctx): return _item_struct(ctx, "RESUMEN")


def item_re_autores(ctx: Ctx):
    """Não deve haver citação de autores nos resumos."""
    from citations import author_hits, numeric_cite_hits
    desc = "Não deve haver citação de autores nos resumos"
    notes, found = [], []
    for key in VERSIONS:
        for p in abstract_content(ctx, key):
            for s, e, t in author_hits(p) + numeric_cite_hits(p):
                found.append(f"{key}: “{t}”")
                notes.append(note(p, f"Resumos não devem conter citações (“{t}”). Remova.", s, e))
    if found:
        return res("re.autores", desc, "NA", "Citações encontradas nos resumos: " + fmt_list(found, 4), notes)
    return res("re.autores", desc, "A", "Nenhuma citação de autores nos resumos")
