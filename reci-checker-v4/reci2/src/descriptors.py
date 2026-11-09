"""DESCRITORES — abaixo dos resumos, 3 a 5, rótulos em negrito e itálico/ponto final."""
import re

from common import Ctx, fmt_list, note, res

LABELS = {
    "RESUMO": ("Descritores", r"Descritores|Palavras[-\s]chave|Unitermos"),
    "ABSTRACT": ("Keywords", r"Keywords|Key\s+words"),
    "RESUMEN": ("Palabras Clave", r"Palabras[-\s]+clave|Descriptores"),
}


def _find(ctx: Ctx, key):
    canon, rx = LABELS[key]
    pat = re.compile(rf"^\s*({rx})\s*:", re.IGNORECASE)
    for p in ctx.sections.get(key):
        m = pat.match(p.text)
        if m:
            return p, m, canon
    return None, None, canon


def _descriptors(p, m):
    body = p.text[m.end():]
    return body, [d.strip() for d in re.split(r"[.;]", body) if d.strip()]


def item_de_abaixo(ctx: Ctx):
    desc = "Apresentados abaixo de cada versão do resumo, citados nos idiomas português, inglês e espanhol"
    missing = [LABELS[k][0] for k in LABELS if _find(ctx, k)[0] is None]
    if missing:
        notes = []
        for k in LABELS:
            if _find(ctx, k)[0] is None and ctx.sections.get(k):
                notes.append(note(ctx.sections.get(k)[-1], f"Inclua abaixo deste resumo a linha “{LABELS[k][0]}: ...”."))
        return res("de.abaixo", desc, "NA", f"Não encontrados abaixo do resumo: {', '.join(missing)} (formato esperado: 'Descritores: ...')", notes)
    return res("de.abaixo", desc, "A", "Descritores, Keywords e Palabras Clave encontrados abaixo das três versões")


def item_de_quantidade(ctx: Ctx):
    desc = "Apresenta de 3 a 5 descritores, segundo o DeCS/BIREME"
    msgs, notes, ok = [], [], True
    for key in LABELS:
        p, m, canon = _find(ctx, key)
        if p is None:
            ok = False
            msgs.append(f"{canon}: não encontrado")
            continue
        _, ds = _descriptors(p, m)
        if not 3 <= len(ds) <= 5:
            ok = False
            msgs.append(f"{canon}: {len(ds)} (esperado 3-5) em {ctx.where(p)}")
            notes.append(note(p, f"{canon}: {len(ds)} termos; use de 3 a 5 descritores do DeCS."))
        else:
            msgs.append(f"{canon}: {len(ds)}")
    return res("de.quantidade", desc, "A" if ok else "NA", "; ".join(msgs) + ". Conferência no DeCS (decs.bvsalud.org) deve ser manual.", notes)


def item_de_termos(ctx: Ctx):
    desc = "Utiliza as terminologias 'Descritores', 'Keywords' e 'Palabras Clave', em negrito, com a primeira letra maiúscula, alinhadas à esquerda"
    msgs, notes = [], []
    for key in LABELS:
        p, m, canon = _find(ctx, key)
        if p is None:
            msgs.append(f"'{canon}' não encontrado")
            continue
        issues = []
        if m.group(1) != canon:
            issues.append(f"'{m.group(1)}' deveria ser '{canon}'")
        runs = p.runs_in(m.start(1), m.end(1))
        if not runs or not all(r.bold for r in runs):
            issues.append(f"'{canon}' não está em negrito")
        if p.align in ("center", "right", "justify"):
            issues.append(f"'{canon}' não está alinhado à esquerda ({p.align})")
        if issues:
            msgs.append("; ".join(issues) + f" ({ctx.where(p)})")
            notes.append(note(p, "; ".join(issues) + ".", m.start(1), m.end(1)))
    return res("de.termos", desc, "NA" if msgs else "A", "; ".join(msgs) if msgs else "Rótulos em negrito, grafia correta e alinhados à esquerda", notes)


def item_de_italico(ctx: Ctx):
    desc = "Descritores, Keywords e Palabras Clave grifados em itálico, separados por ponto final, com a primeira letra de cada descritor em maiúscula"
    msgs, notes = [], []
    for key in LABELS:
        p, m, canon = _find(ctx, key)
        if p is None:
            msgs.append(f"'{canon}' não encontrado")
            continue
        body, ds = _descriptors(p, m)
        runs = p.runs_in(m.end(), len(p.text))
        why = []
        if not runs or not all(r.italic for r in runs):
            why.append("não estão em itálico")
        if ";" in body or "," in body:
            why.append(f"separados por {'ponto e vírgula' if ';' in body else 'vírgula'} (use ponto final)")
        elif len(ds) > 1 and body.count(".") < len(ds):
            why.append("sem ponto final entre/após os termos")
        low = [d for d in ds if d[:1].islower()]
        if low:
            why.append(f"iniciar com maiúscula ({fmt_list(low, 3, ', ')})")
        if why:
            msgs.append(f"{canon}: " + ", ".join(why) + f" ({ctx.where(p)})")
            notes.append(note(p, f"Descritores ({canon}): " + ", ".join(why) + ". Ex.: Descritores: HIV. Covid-19. Isolamento social.", m.end(), len(p.text)))
    return res("de.italico", desc, "NA" if msgs else "A", "; ".join(msgs) if msgs else "Descritores em itálico, separados por ponto final", notes)
