"""Gera o Checklist em Word a partir do modelo da RECI (check_list_texto_dois.docx), preservando layout,
cabeçalho e os links "Clique aqui para baixar: ...", com as alterações da RECI (ver catalog.OVERRIDES)."""
import copy
import re
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX as C
from docx.oxml.ns import qn
from docx.shared import Pt

from catalog import CATALOG, CATEGORY_TEXT, OVERRIDES
from common import STATUS_LABEL, strip_accents

COL = {"A": (1, C.TURQUOISE), "AP": (2, C.BRIGHT_GREEN), "NA": (3, C.YELLOW), "NSA": (4, C.GRAY_25)}


def _key(t: str) -> str:
    return re.sub(r"\W+", "", strip_accents(t).lower())[:35]


def _cell_text(tc) -> str:
    return " ".join("".join(t.text or "" for t in p.iter(qn("w:t"))) for p in tc.iter(qn("w:p"))).strip()


def _has_link(p_el) -> bool:
    return p_el.find(qn("w:hyperlink")) is not None


def _clear_runs(p):
    for r in list(p._p):
        if r.tag in (qn("w:r"), qn("w:proofErr"), qn("w:sdt")):
            p._p.remove(r)


def _set_mark(cell, status):
    cell_p = cell.paragraphs[0]
    for extra in cell.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)
    _clear_runs(cell_p)
    if status in COL:
        run = cell_p.add_run("x")
        run.font.highlight_color = COL[status][1]
        run.bold = True
    cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _set_comment(cell, text, keep_links=True):
    """Mantém parágrafos com hiperlink ("Clique aqui para baixar") e substitui o restante pelo comentário."""
    paras = list(cell.paragraphs)
    link_paras = [p for p in paras if keep_links and _has_link(p._p)]
    for p in paras:
        if p not in link_paras:
            if p is paras[0] and not link_paras:
                _clear_runs(p)
            else:
                p._element.getparent().remove(p._element)
    first_free = next((p for p in cell.paragraphs if not _has_link(p._p)), None)
    lines = [l for l in text.split("\n") if l.strip()]
    for k, line in enumerate(lines):
        p = first_free if (k == 0 and first_free is not None) else cell.add_paragraph()
        _clear_runs(p) if p is first_free and k == 0 else None
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(line)
        run.font.size = Pt(9)


def _apply_override(cell, ops):
    for op in ops:
        if op[0] == "replace":
            done = False
            for p in cell.paragraphs:
                for r in p.runs:
                    if op[1] in r.text:
                        r.text = r.text.replace(op[1], op[2])
                        done = True
                if not done and op[1] in p.text:       # texto dividido em vários runs
                    full = p.text.replace(op[1], op[2])
                    runs = p.runs
                    runs[0].text = full
                    for r in runs[1:]:
                        r._r.getparent().remove(r._r)
                    done = True
        elif op[0] == "append":
            p = cell.paragraphs[-1]
            base = p.runs[-1] if p.runs else None
            r = p.add_run(op[1])
            if base is not None and base._r.rPr is not None:
                r._r.insert(0, copy.deepcopy(base._r.rPr))
        elif op[0] == "append_par":
            last = cell.paragraphs[-1]
            newp = copy.deepcopy(last._p)
            last._p.addnext(newp)
            from docx.text.paragraph import Paragraph
            np_ = Paragraph(newp, last._parent)
            for r in np_.runs[1:]:
                r._r.getparent().remove(r._r)
            if np_.runs:
                np_.runs[0].text = op[1]
            else:
                np_.add_run(op[1])


def fill_checklist(ctx, cat, sections, template: Path, out: Path, title: str = "", manuscript_id: str = "") -> list[str]:
    warnings: list[str] = []
    d = docx.Document(str(template))
    results = {r["item"]: r for _, rs in sections for r in rs}

    # --- cabeçalho: ID e título ----------------------------------------------------------------
    paras = d.paragraphs
    for i, p in enumerate(paras):
        if p.text.startswith("CHECKLIST MANUSCRITO"):
            if len(p.runs) >= 2:
                p.runs[1].text = manuscript_id
                for r in p.runs[2:]:
                    r._r.getparent().remove(r._r)
            for q in paras[i + 1:i + 3]:
                if q.text.strip() and q.runs:
                    q.runs[0].text = title
                    for r in q.runs[1:]:
                        r._r.getparent().remove(r._r)
                    break
            break

    # --- categoria (tabela de 1 coluna com a regra de referências) ------------------------------
    for table in d.tables:
        for row in table.rows:
            tcs = row._tr.findall(qn("w:tc"))
            if len(tcs) == 1 and "referências" in _cell_text(tcs[0]).lower() and "mínimo" in _cell_text(tcs[0]).lower():
                cell = row.cells[0]
                st = cat["status"]
                for extra in cell.paragraphs[1:]:
                    extra._element.getparent().remove(extra._element)
                p = cell.paragraphs[0]
                _clear_runs(p)
                p.add_run(CATEGORY_TEXT + " — ")
                r = p.add_run(STATUS_LABEL.get(st, st))
                r.bold = True
                if st in COL:
                    r.font.highlight_color = COL[st][1]
                p.add_run(f". {cat['comments']}")

    # --- linhas de itens -----------------------------------------------------------------------------
    rows = []
    for table in d.tables:
        for row in table.rows:
            tcs = row._tr.findall(qn("w:tc"))
            if len(tcs) == 6 and _cell_text(tcs[0]):
                rows.append(row)
    if len(rows) != len(CATALOG):
        warnings.append(f"O modelo tem {len(rows)} linhas de itens; o catálogo espera {len(CATALOG)}")
    for row, item in zip(rows, CATALOG):
        if _key(_cell_text(row._tr.findall(qn("w:tc"))[0])) != _key(item.text):
            warnings.append(f"Linha do modelo não confere com o item {item.id}: “{_cell_text(row._tr.findall(qn('w:tc'))[0])[:50]}”")
        r = results.get(item.id)
        if r is None:
            continue
        cells = row.cells
        if item.id in OVERRIDES:
            _apply_override(cells[0], OVERRIDES[item.id])
        for c in range(1, 5):
            _set_mark(cells[c], None)
        st = r["status"]
        if st in COL:
            _set_mark(cells[COL[st][0]], st)
        text = r["comments"]
        if st == "-":
            text = "[Verificar manualmente] " + text
        _set_comment(cells[5], text)
    d.save(str(out))
    return warnings
