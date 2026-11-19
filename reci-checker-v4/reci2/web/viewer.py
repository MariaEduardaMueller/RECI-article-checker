"""Visualização no navegador: (1) artigo com os trechos comentados em destaque + comentários ao lado;
(2) Checklist preenchido em tabela colorida. Não depende de bibliotecas externas além das do projeto."""
from __future__ import annotations

import base64
import html
import json
import re
from pathlib import Path

from document_model import _iter_blocks, _local, _w, load_document

A_BLIP = "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"

STATUS_CLASS = {"A": "ok", "AP": "part", "NA": "bad", "NSA": "na", "-": "man", "SKIP": "na"}
STATUS_TEXT = {"A": "Atende", "AP": "Atende parcialmente", "NA": "Não atende", "NSA": "Não se aplica",
               "-": "Verificar manualmente", "SKIP": "Fora do escopo"}

BASE_CSS = """
:root{--navy:#0b1d51;--beige:#d9cfcd;--ok:#bde7f5;--part:#c6efce;--bad:#fff2a8;--na:#e5e5e5;--man:#fff;}
*{box-sizing:border-box}body{margin:0;font-family:Segoe UI,system-ui,Arial,sans-serif;background:#f3efee;color:#1c2333}
"""


def _e(s) -> str:
    return html.escape(str(s), quote=True)


# ------------------------------------------------------------------------------------ artigo comentado
def _img_tags(p_el, docx_obj) -> str:
    out = []
    for blip in p_el.iter(A_BLIP):
        try:
            part = docx_obj.part.related_parts[blip.get(R_EMBED)]
            mime = part.content_type or "image/png"
            out.append(f'<img alt="imagem do artigo" src="data:{mime};base64,{base64.b64encode(part.blob).decode()}">')
        except Exception:
            out.append('<span class="noimg">[imagem]</span>')
    return "".join(out)


def _render_para(p_el, para, docx_obj) -> str:
    imgs = _img_tags(p_el, docx_obj)
    if para is None:
        txt = "".join(t.text or "" for t in p_el.iter(_w("t")))
        return f"<p>{imgs}{_e(txt)}</p>" if (txt or imgs) else "<p class='empty'>&nbsp;</p>"
    spans = {id(r): (a, b) for a, b, r in para.spans}
    text = para.text
    events, offset = [], 0
    for el in p_el.iter():
        loc = _local(el.tag)
        if loc == "r" and id(el) in spans:
            offset = spans[id(el)][1]
        elif loc == "commentRangeStart":
            events.append((offset, "s", el.get(_w("id"))))
        elif loc == "commentRangeEnd":
            events.append((offset, "e", el.get(_w("id"))))
    bounds = {0, len(text)} | {o for o, _, _ in events}
    pos = 0
    for r in para.runs:
        pos += len(r.text)
        bounds.add(pos)
    cuts = sorted(bounds)
    run_at, acc = [], 0
    for r in para.runs:
        run_at.append((acc, acc + len(r.text), r))
        acc += len(r.text)

    def run_for(a):
        for s, e, r in run_at:
            if s <= a < e:
                return r
        return None

    active, ei, out = [], 0, []
    for a, b in zip(cuts, cuts[1:]):
        while ei < len(events) and events[ei][0] <= a:
            _, kind, cid = events[ei]
            if kind == "s":
                active.append(cid)
            elif cid in active:
                active.remove(cid)
            ei += 1
        seg = text[a:b]
        if not seg:
            continue
        s = _e(seg).replace("\t", "&emsp;").replace("\n", "<br>")
        r = run_for(a)
        if r is not None:
            if r.bold:
                s = f"<b>{s}</b>"
            if r.italic:
                s = f"<i>{s}</i>"
            if r.superscript:
                s = f"<sup>{s}</sup>"
            if r.link:
                s = f"<u>{s}</u>"
        if active:
            s = f'<mark data-c="{" ".join(active)}">{s}</mark>'
        out.append(s)
    style = []
    if para.align in ("center", "right", "justify"):
        style.append(f"text-align:{para.align}")
    if para.first_indent and para.first_indent > 0:
        style.append(f"text-indent:{min(para.first_indent, 3):.1f}cm")
    body = "".join(out)
    if not body.strip() and not imgs:
        return "<p class='empty'>&nbsp;</p>"
    return f'<p style="{";".join(style)}">{imgs}{body}</p>'


def render_article_html(path: Path, title: str = "Artigo com comentários") -> str:
    doc = load_document(path)
    d = doc.docx_obj
    pmap = {id(p.el): p for p in doc.paragraphs}
    comments = {}
    try:
        for c in d.comments:
            comments[str(c.comment_id)] = c
    except Exception:
        pass
    parts = []
    for blk in _iter_blocks(d.element.body):
        if _local(blk.tag) == "p":
            parts.append(_render_para(blk, pmap.get(id(blk)), d))
        else:
            rows = []
            for tr in blk.iterchildren(_w("tr")):
                cells = []
                for tc in tr.iterchildren(_w("tc")):
                    cells.append("<td>" + "".join(_render_para(p, pmap.get(id(p)), d) for p in tc.iter(_w("p"))) + "</td>")
                rows.append("<tr>" + "".join(cells) + "</tr>")
            parts.append("<table>" + "".join(rows) + "</table>")
    side = []
    for i, (cid, c) in enumerate(sorted(comments.items(), key=lambda kv: int(kv[0])), 1):
        lines = [l for l in c.text.split("\n") if l.strip()]
        tag, msg = (lines[0], " ".join(lines[1:])) if lines and lines[0].startswith("[") else ("", " ".join(lines))
        side.append(f'<div class="cm" id="cm{cid}" data-c="{cid}"><div class="n">Comentário {i}</div>'
                    f'{"<div class=tag>" + _e(tag) + "</div>" if tag else ""}<div class="t">{_e(msg)}</div></div>')
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{_e(title)}</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{BASE_CSS}
.wrap{{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:18px;max-width:1280px;margin:0 auto;padding:16px}}
.sheet{{background:#fff;padding:34px 44px;border-radius:6px;box-shadow:0 1px 6px #0002;font-family:'Times New Roman',serif;font-size:16px;line-height:1.55}}
.sheet p{{margin:0 0 .6em}}.sheet p.empty{{margin:0;line-height:.6}}.sheet img{{max-width:100%;display:block;margin:8px auto}}
.sheet table{{border-collapse:collapse;margin:10px 0;width:100%}}.sheet td{{border-top:1px solid #aaa;border-bottom:1px solid #aaa;padding:3px 8px;font-size:14px}}.sheet td p{{margin:0}}
mark{{background:#ffe27a;cursor:pointer;border-radius:2px;padding:0 1px}}mark.on{{background:#ffb347;outline:2px solid #e07b00}}
.side{{position:sticky;top:12px;align-self:start;max-height:calc(100vh - 24px);overflow:auto}}
.cm{{background:#fff;border-left:5px solid #e0a800;border-radius:5px;padding:9px 11px;margin-bottom:9px;box-shadow:0 1px 4px #0002;font-size:13.5px;cursor:pointer}}
.cm.on{{border-color:#e07b00;background:#fff6e0}}.cm .n{{font-weight:700;color:var(--navy);font-size:12px}}.cm .tag{{font-size:11.5px;color:#667;margin:2px 0 4px}}
.top{{background:var(--navy);color:#fff;padding:10px 18px;font-size:14px;position:sticky;top:0;z-index:5}}
@media(max-width:900px){{.wrap{{grid-template-columns:1fr}}.side{{position:static;max-height:none}}}}
</style></head><body>
<div class="top"><b>{_e(title)}</b> — {len(comments)} comentário(s). Clique em um trecho destacado (ou em um comentário) para localizar.</div>
<div class="wrap"><div class="sheet">{''.join(parts)}</div><div class="side">{''.join(side) or '<div class=cm>Nenhum comentário: nada a corrigir foi encontrado.</div>'}</div></div>
<script>
const cms=[...document.querySelectorAll('.cm')];
function clear(){{document.querySelectorAll('.on').forEach(e=>e.classList.remove('on'));}}
function show(ids,scrollTo){{clear();ids.forEach(id=>{{const c=document.getElementById('cm'+id);if(c)c.classList.add('on');
 document.querySelectorAll('mark').forEach(m=>{{if(m.dataset.c.split(' ').includes(id))m.classList.add('on');}});}});
 if(scrollTo==='cm'){{const c=document.getElementById('cm'+ids[0]);if(c)c.scrollIntoView({{behavior:'smooth',block:'center'}});}}
 if(scrollTo==='mark'){{const m=document.querySelector('mark.on');if(m)m.scrollIntoView({{behavior:'smooth',block:'center'}});}}}}
document.querySelectorAll('mark').forEach(m=>m.addEventListener('click',()=>show(m.dataset.c.split(' '),'cm')));
cms.forEach(c=>c.addEventListener('click',()=>show([c.dataset.c],'mark')));
</script></body></html>"""


# ------------------------------------------------------------------------------------ checklist
def render_checklist_html(json_path: Path, title: str = "Checklist preenchido") -> str:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    resumo = data.get("resumo", {})
    chips = "".join(f'<button class="chip {STATUS_CLASS[k]}" data-f="{k}">{STATUS_TEXT[k]}: <b>{resumo.get(k, 0)}</b></button>'
                    for k in ("A", "AP", "NA", "NSA", "-"))
    rows = []
    cat = data.get("categoria")
    sections = [("CATEGORIA DO MANUSCRITO — Artigo original", [cat])] if cat else []
    sections += [(s["nome"], s["itens"]) for s in data.get("secoes", [])]
    for name, items in sections:
        rows.append(f'<tr class="sec"><td colspan="3">{_e(name)}</td></tr>')
        for it in items:
            st = it["status"]
            n = len(it.get("comentarios_no_texto", []))
            note = f'<div class="nt">{n} comentário(s) no artigo</div>' if n else ""
            item_html = "<br>".join(_e(l) for l in it["item"].split("\n"))
            rows.append(f'<tr data-s="{_e(st)}"><td class="it">{item_html}</td>'
                        f'<td class="st {STATUS_CLASS.get(st, "man")}">{STATUS_TEXT.get(st, st)}</td>'
                        f'<td class="cmt">{_e(it["comentarios"]) or "—"}{note}</td></tr>')
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{_e(title)}</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{BASE_CSS}
.top{{background:var(--navy);color:#fff;padding:12px 18px;font-size:15px}}.wrap{{max-width:1200px;margin:0 auto;padding:16px}}
.chips{{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 14px}}.chip{{border:1px solid #0003;border-radius:18px;padding:6px 12px;cursor:pointer;font-size:13.5px;background:#fff}}
.chip.on{{outline:2px solid var(--navy)}}.ok{{background:var(--ok)}}.part{{background:var(--part)}}.bad{{background:var(--bad)}}.na{{background:var(--na)}}.man{{background:#fff}}
table{{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 1px 6px #0002}}td{{border:1px solid #cfcfcf;padding:7px 9px;vertical-align:top;font-size:13.5px}}
tr.sec td{{background:#d9d9d9;font-weight:700;color:var(--navy)}}td.it{{width:38%}}td.st{{width:11%;font-weight:600;text-align:center}}td.cmt{{width:51%}}
.nt{{margin-top:5px;font-size:12px;color:#556}}.leg{{font-size:13px;color:#445;margin-bottom:6px}}
</style></head><body><div class="top"><b>{_e(title)}</b> — {_e(data.get('meta', {}).get('arquivo', ''))}</div>
<div class="wrap"><div class="leg">Filtre pelo status clicando nos botões abaixo. Azul = atende · verde = parcialmente · amarelo = não atende · cinza = não se aplica.</div>
<div class="chips">{chips}<button class="chip" data-f="">Mostrar todos</button></div>
<table>{''.join(rows)}</table></div>
<script>
document.querySelectorAll('.chip').forEach(b=>b.addEventListener('click',()=>{{
 const f=b.dataset.f;document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on',x===b&&f!==''));
 document.querySelectorAll('tr[data-s]').forEach(r=>r.style.display=(!f||r.dataset.s===f)?'':'none');
 document.querySelectorAll('tr.sec').forEach(s=>{{let n=s.nextElementSibling,vis=false;while(n&&!n.classList.contains('sec')){{if(n.style.display!=='none')vis=true;n=n.nextElementSibling;}}s.style.display=vis||!f?'':'none';}});
}}));
</script></body></html>"""
