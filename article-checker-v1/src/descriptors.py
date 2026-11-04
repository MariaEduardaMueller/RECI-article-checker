"""DESCRITORES — itens 30 a 33."""
import re

from common import Ctx, fmt_list, res

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


def item_30(ctx: Ctx):
    desc = "Apresentados abaixo de cada versão do resumo, citados nos idiomas português, inglês e espanhol"
    missing = [LABELS[k][0] for k in LABELS if _find(ctx, k)[0] is None]
    if missing:
        return res(30, desc, "NA", f"Não encontrados abaixo do resumo: {', '.join(missing)} (formato esperado: 'Descritores: ...')")
    return res(30, desc, "A", "Descritores, Keywords e Palabras Clave encontrados abaixo das três versões")


def item_31(ctx: Ctx):
    desc = "Apresenta de 3 a 5 descritores, segundo o DeCS/BIREME"
    msgs, ok = [], True
    for key in LABELS:
        p, m, canon = _find(ctx, key)
        if p is None:
            ok = False
            msgs.append(f"{canon}: não encontrado")
            continue
        _, ds = _descriptors(p, m)
        if not 3 <= len(ds) <= 5:
            ok = False
            msgs.append(f"{canon}: {len(ds)} (esperado 3-5)")
        else:
            msgs.append(f"{canon}: {len(ds)}")
    return res(31, desc, "A" if ok else "NA", "; ".join(msgs) + ". Conferência no DeCS (decs.bvsalud.org) deve ser manual.")


def item_32(ctx: Ctx):
    desc = "Utiliza as terminologias 'Descritores', 'Keywords' e 'Palabras Clave', em negrito, com a primeira letra maiúscula, alinhadas à esquerda"
    msgs = []
    for key in LABELS:
        p, m, canon = _find(ctx, key)
        if p is None:
            msgs.append(f"'{canon}' não encontrado")
            continue
        label_text = m.group(1)
        if label_text != canon:
            msgs.append(f"'{label_text}' deveria ser '{canon}'")
        runs = p.runs_in(m.start(1), m.end(1))
        if not runs or not all(r.bold for r in runs):
            msgs.append(f"'{canon}' não está em negrito")
        if p.align in ("center", "right") or (p.align == "justify" and ctx.doc.exact):
            msgs.append(f"'{canon}' não está alinhado à esquerda ({p.align})")
    return res(32, desc, "NA" if msgs else "A", "; ".join(msgs) if msgs else "Rótulos em negrito, grafia correta e alinhados à esquerda")


def item_33(ctx: Ctx):
    desc = "Descritores, Keywords e Palabras Clave grifados em itálico, separados por ponto final, com a primeira letra de cada descritor em maiúscula"
    msgs = []
    for key in LABELS:
        p, m, canon = _find(ctx, key)
        if p is None:
            msgs.append(f"'{canon}' não encontrado")
            continue
        body, ds = _descriptors(p, m)
        runs = p.runs_in(m.end(), len(p.text))
        if not runs or not all(r.italic for r in runs):
            msgs.append(f"descritores de '{canon}' não estão em itálico")
        if ";" in body or "," in body:
            msgs.append(f"descritores de '{canon}' separados por {'ponto e vírgula' if ';' in body else 'vírgula'} (esperado ponto final)")
        elif len(ds) > 1 and body.count(".") < len(ds) - 0:
            msgs.append(f"descritores de '{canon}' sem ponto final entre/após os termos")
        low = [d for d in ds if d[:1].islower()]
        if low:
            msgs.append(f"'{canon}': iniciar com maiúscula ({fmt_list(low, 3, ', ')})")
    return res(33, desc, "NA" if msgs else "A", "; ".join(msgs) if msgs else "Descritores em itálico, separados por ponto final")
