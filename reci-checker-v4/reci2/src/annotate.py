"""Cópia do manuscrito com COMENTÁRIOS do Word nos trechos a corrigir. O texto do artigo NÃO é alterado."""
import copy
from pathlib import Path

from docx.text.paragraph import Paragraph as DPara
from docx.text.run import Run as DRun

from catalog import BY_ID, CATALOG
from common import Ctx
from document_model import _local, _run_text, _skip_run, _w

AUTHOR, INITIALS = "reci-checker", "RC"


def _live_runs(p_el):
    out, pos = [], 0
    for r in p_el.iter(_w("r")):
        if _skip_run(r, p_el):
            continue
        t = _run_text(r)
        if t:
            out.append([pos, pos + len(t), r])
            pos += len(t)
    return out


def _split_at(p_el, offset):
    """Garante um limite de run em `offset` (divide o run se for simples). Não altera o texto."""
    for a, b, r in _live_runs(p_el):
        if a < offset < b:
            ts = [c for c in r if _local(c.tag) == "t"]
            if len(ts) != 1 or any(_local(c.tag) not in ("t", "rPr") for c in r):
                return
            txt, k = ts[0].text or "", offset - a
            r2 = copy.deepcopy(r)
            ts[0].text = txt[:k]
            ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t2 = [c for c in r2 if _local(c.tag) == "t"][0]
            t2.text = txt[k:]
            t2.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            r.addnext(r2)
            return


def _anchor_runs(p_el, start, end):
    if start is not None and end is not None:
        _split_at(p_el, start)
        _split_at(p_el, end)
    runs = _live_runs(p_el)
    if start is None or end is None:
        sel = runs
    else:
        sel = [x for x in runs if x[1] > start and x[0] < end]
    return [x[2] for x in sel]


def _title(item_id: str) -> str:
    if item_id == "cat.refs":
        return "Referências nos últimos 5 anos"
    it = BY_ID[item_id]
    first = it.text.split("\n")[0]
    return (first[:75] + "…") if len(first) > 75 else first


def write_commented(ctx: Ctx, sections, cat, out: Path) -> int:
    d = ctx.doc.docx_obj
    if not hasattr(d, "add_comment"):
        raise RuntimeError("python-docx antigo: comentários exigem a versão 1.2 ou superior (pip install -U python-docx)")
    paras = ctx.doc.paragraphs
    first_text = next((p for p in paras if p.stripped and not p.in_table), None)
    seen, n = set(), 0
    for r in [cat] + [x for _, rs in sections for x in rs]:
        for nt in r.get("notes", []):
            key = (nt["para"], nt["start"], nt["end"], nt["text"])
            if key in seen:
                continue
            seen.add(key)
            p = paras[nt["para"]] if nt["para"] is not None else first_text
            if p is None or p.el is None:
                continue
            runs = _anchor_runs(p.el, nt["start"], nt["end"])
            if not runs:
                continue
            parent = DPara(p.el, d._body)
            word_runs = [DRun(x, parent) for x in runs]
            section = BY_ID[r["item"]].section if r["item"] in BY_ID else "CATEGORIA"
            d.add_comment(runs=[word_runs[0], word_runs[-1]], text=f"[{section.capitalize()} — {_title(r['item'])}]\n{nt['text']}", author=AUTHOR, initials=INITIALS)
            n += 1
    d.save(str(out))
    return n
