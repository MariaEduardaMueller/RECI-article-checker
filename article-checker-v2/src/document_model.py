"""
Modelo de documento (.docx).

Todas as verificações do reci-checker trabalham sobre `Document`: leitura exata via XML
(estilos, herança de formatação, espaçamento, recuos, bordas de tabelas, hiperlinks,
resolução de imagens...). Cada parágrafo guarda o elemento XML de origem (`el`) e o mapa
caractere -> run (`spans`), usados para ancorar os comentários na cópia comentada do artigo.

Valores desconhecidos são `None` — as verificações devem tratar `None` como
"não foi possível verificar", nunca como erro do autor.
"""
from __future__ import annotations

import re
import statistics
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
C_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


# ----------------------------------------------------------------------------
# Estruturas
# ----------------------------------------------------------------------------
@dataclass
class Run:
    text: str
    bold: bool | None = None
    italic: bool | None = None
    size: float | None = None       # pontos
    font: str | None = None
    superscript: bool = False
    link: bool = False                   # dentro de hiperlink


@dataclass
class Para:
    runs: list[Run]
    index: int = 0
    style: str = ""
    align: str | None = None             # left | center | right | justify
    line_spacing: float | None = None    # múltiplo (1.0 = simples, 1.5 = 1,5 linha)
    space_before: float | None = None    # pontos
    space_after: float | None = None     # pontos
    in_table: bool = False
    table_index: int | None = None
    n_images: int = 0
    numbered: bool = False               # lista numerada automática do Word
    page: int | None = None
    line_runs: list | None = None
    first_indent: float | None = None    # recuo da 1ª linha em cm (negativo = deslocamento)
    left_indent: float | None = None     # recuo à esquerda em cm
    el: object = None                    # elemento <w:p> de origem
    spans: list = field(default_factory=list)   # [(início, fim, <w:r>)] sobre .text

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)

    @property
    def stripped(self) -> str:
        return self.text.strip()

    def visible_runs(self) -> list[Run]:
        return [r for r in self.runs if r.text.strip()]

    def all_bold(self) -> bool:
        v = self.visible_runs()
        return bool(v) and all(r.bold for r in v)

    def any_bold(self) -> bool:
        return any(r.bold for r in self.visible_runs())

    def all_italic(self) -> bool:
        v = self.visible_runs()
        return bool(v) and all(r.italic for r in v)

    def any_italic(self) -> bool:
        return any(r.italic for r in self.visible_runs())

    def sizes(self) -> set[float]:
        return {r.size for r in self.visible_runs() if r.size}

    def fonts(self) -> set[str]:
        return {r.font for r in self.visible_runs() if r.font}

    def runs_in(self, start: int, end: int) -> list[Run]:
        """Runs (com texto visível) que cobrem o intervalo [start, end) do texto."""
        out, pos = [], 0
        for r in self.runs:
            r_start, r_end = pos, pos + len(r.text)
            pos = r_end
            if r_end <= start or r_start >= end:
                continue
            seg = r.text[max(start, r_start) - r_start:min(end, r_end) - r_start]
            if seg.strip():
                out.append(r)
        return out

    def visual_lines(self) -> list[list[Run]]:
        """Linhas como aparecem na página (PDF) ou separadas por quebra manual (.docx)."""
        return self.line_runs if self.line_runs else self.lines()

    def lines(self) -> list[list[Run]]:
        """Divide os runs nas quebras de linha manuais (Shift+Enter)."""
        lines: list[list[Run]] = [[]]
        for r in self.runs:
            parts = r.text.split("\n")
            for i, part in enumerate(parts):
                if i > 0:
                    lines.append([])
                if part:
                    lines[-1].append(Run(part, r.bold, r.italic, r.size, r.font, r.superscript, r.link))
        return [l for l in lines if "".join(x.text for x in l).strip()]


@dataclass
class TableInfo:
    index: int
    rows: list[list[str]]
    first_para: int
    last_para: int
    borders: dict | None = None          # só .docx
    shaded: bool | None = None           # só .docx


@dataclass
class ImageInfo:
    para_index: int
    kind: str = "picture"                # picture | chart
    width_in: float | None = None
    px: tuple[int, int] | None = None
    dpi: float | None = None
    page: int | None = None


@dataclass
class Document:
    path: Path
    fmt: str                             # docx | pdf
    paragraphs: list[Para]
    tables: list[TableInfo] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)
    props: dict = field(default_factory=dict)
    size_bytes: int = 0
    pages: int | None = None
    exact: bool = True
    docx_obj: object = None              # python-docx Document (para gravar comentários)

    @property
    def body(self) -> list[Para]:
        return [p for p in self.paragraphs if not p.in_table]

    @property
    def text(self) -> str:
        return "\n".join(p.stripped for p in self.paragraphs if p.stripped)


# ----------------------------------------------------------------------------
# DOCX
# ----------------------------------------------------------------------------
class _Styles:
    """Resolve a herança de formatação do Word (run > estilo de caractere >
    estilo de parágrafo > padrões do documento)."""

    def __init__(self, docx_document, theme_fonts: dict):
        root = docx_document.styles.element
        self.theme = theme_fonts
        self.by_id: dict[str, dict] = {}
        self.default_para: str | None = None
        self.doc_rpr = self.doc_ppr = None

        dd = root.find(_w("docDefaults"))
        if dd is not None:
            self.doc_rpr = dd.find(f"{_w('rPrDefault')}/{_w('rPr')}")
            self.doc_ppr = dd.find(f"{_w('pPrDefault')}/{_w('pPr')}")

        for st in root.findall(_w("style")):
            sid = st.get(_w("styleId"))
            based = st.find(_w("basedOn"))
            self.by_id[sid] = {
                "type": st.get(_w("type")),
                "based": based.get(_w("val")) if based is not None else None,
                "rpr": st.find(_w("rPr")),
                "ppr": st.find(_w("pPr")),
                "tblpr": st.find(_w("tblPr")),
            }
            if st.get(_w("type")) == "paragraph" and st.get(_w("default")) in ("1", "true"):
                self.default_para = sid

    def chain(self, sid):
        out, seen = [], set()
        while sid and sid in self.by_id and sid not in seen:
            seen.add(sid)
            out.append(self.by_id[sid])
            sid = self.by_id[sid]["based"]
        return out

    # -- propriedades de run -------------------------------------------------
    @staticmethod
    def _toggle(rprs, tag):
        for rpr in rprs:
            if rpr is None:
                continue
            el = rpr.find(_w(tag))
            if el is not None:
                return el.get(_w("val")) not in ("0", "false", "off")
        return None

    def _font(self, rprs):
        for rpr in rprs:
            if rpr is None:
                continue
            rf = rpr.find(_w("rFonts"))
            if rf is None:
                continue
            for attr in ("ascii", "hAnsi"):
                if rf.get(_w(attr)):
                    return rf.get(_w(attr))
            for attr in ("asciiTheme", "hAnsiTheme"):
                th = rf.get(_w(attr))
                if th:
                    return self.theme.get("major" if th.startswith("major") else "minor")
        return None

    def _size(self, rprs):
        for rpr in rprs:
            if rpr is None:
                continue
            sz = rpr.find(_w("sz"))
            if sz is not None and sz.get(_w("val")):
                return int(sz.get(_w("val"))) / 2
        return None

    def _sup(self, rprs):
        for rpr in rprs:
            if rpr is None:
                continue
            va = rpr.find(_w("vertAlign"))
            if va is not None:
                return va.get(_w("val")) == "superscript"
        return False

    def run_props(self, r_el, para_chain):
        rpr = r_el.find(_w("rPr"))
        rs = rpr.find(_w("rStyle")) if rpr is not None else None
        rchain = self.chain(rs.get(_w("val"))) if rs is not None else []
        rprs = [rpr] + [s["rpr"] for s in rchain] + [s["rpr"] for s in para_chain] + [self.doc_rpr]
        bold = self._toggle(rprs, "b")
        italic = self._toggle(rprs, "i")
        return Run("", bool(bold), bool(italic), self._size(rprs), self._font(rprs), self._sup(rprs))

    def indent_props(self, p_el, para_chain):
        pprs = [p_el.find(_w("pPr"))] + [s["ppr"] for s in para_chain] + [self.doc_ppr]
        first = left = None
        for pp in pprs:
            ind = pp.find(_w("ind")) if pp is not None else None
            if ind is None:
                continue
            if first is None:
                if ind.get(_w("firstLine")) is not None:
                    first = int(ind.get(_w("firstLine"))) / 567
                elif ind.get(_w("hanging")) is not None:
                    first = -int(ind.get(_w("hanging"))) / 567
            if left is None:
                v = ind.get(_w("left")) or ind.get(_w("start"))
                if v is not None:
                    left = int(v) / 567
        return first, left

    # -- propriedades de parágrafo ------------------------------------------
    def para_props(self, p_el, para_chain):
        ppr = p_el.find(_w("pPr"))
        pprs = [ppr] + [s["ppr"] for s in para_chain] + [self.doc_ppr]

        def spacing_attr(name):
            for pp in pprs:
                if pp is None:
                    continue
                sp = pp.find(_w("spacing"))
                if sp is not None and sp.get(_w(name)) is not None:
                    return sp.get(_w(name))
            return None

        align = None
        for pp in pprs:
            if pp is None:
                continue
            jc = pp.find(_w("jc"))
            if jc is not None:
                align = {"both": "justify", "distribute": "justify", "start": "left",
                         "end": "right"}.get(jc.get(_w("val")), jc.get(_w("val")))
                break
        align = align or "left"

        line, rule = spacing_attr("line"), spacing_attr("lineRule")
        if line is None:
            ls = 1.0
        elif rule in (None, "auto"):
            ls = int(line) / 240
        else:                                    # exact / atLeast -> estimativa
            ls = None
        after = spacing_attr("after")
        before = spacing_attr("before")
        sa = int(after) / 20 if after is not None else 0.0
        sb = int(before) / 20 if before is not None else 0.0
        if spacing_attr("afterAutospacing") in ("1", "true"):
            sa = 14.0
        if spacing_attr("beforeAutospacing") in ("1", "true"):
            sb = 14.0

        numbered = False
        for pp in pprs:
            if pp is None:
                continue
            np_ = pp.find(_w("numPr"))
            if np_ is not None:
                nid = np_.find(_w("numId"))
                numbered = nid is None or nid.get(_w("val")) != "0"
                break
        return align, ls, sb, sa, numbered


def _theme_fonts(path: Path) -> dict:
    out = {"major": None, "minor": None}
    try:
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(path) as zf:
            name = next((n for n in zf.namelist() if n.startswith("word/theme/theme")), None)
            if not name:
                return out
            root = ET.fromstring(zf.read(name))
        for kind in ("major", "minor"):
            el = root.find(f".//{{{A_NS}}}{kind}Font/{{{A_NS}}}latin")
            if el is not None:
                out[kind] = el.get("typeface")
    except Exception:
        pass
    return out


def _iter_blocks(parent):
    """Itera <w:p> e <w:tbl> em ordem, descendo em <w:sdt> (controles de conteúdo)."""
    for ch in parent.iterchildren():
        t = _local(ch.tag)
        if t in ("p", "tbl"):
            yield ch
        elif t == "sdt":
            content = ch.find(_w("sdtContent"))
            if content is not None:
                yield from _iter_blocks(content)


_SKIP_ANCESTORS = {"del", "moveFrom", "txbxContent", "Fallback"}


def _skip_run(r_el, stop) -> bool:
    a = r_el.getparent()
    while a is not None and a is not stop:
        if _local(a.tag) in _SKIP_ANCESTORS:
            return True
        a = a.getparent()
    return False


def _in_link(r_el, stop) -> bool:
    a = r_el.getparent()
    while a is not None and a is not stop:
        if _local(a.tag) == "hyperlink":
            return True
        if _local(a.tag) == "fldSimple" and "HYPERLINK" in (a.get(_w("instr")) or "").upper():
            return True
        a = a.getparent()
    return False


def _run_text(r_el) -> str:
    out = []
    for ch in r_el:
        t = _local(ch.tag)
        if t == "t":
            out.append(ch.text or "")
        elif t == "tab":
            out.append("\t")
        elif t in ("br", "cr"):
            if ch.get(_w("type")) not in ("page", "column"):
                out.append("\n")
        elif t == "noBreakHyphen":
            out.append("-")
    return "".join(out)


def _merge_runs(runs: list[Run]) -> list[Run]:
    out: list[Run] = []
    for r in runs:
        if out and (out[-1].bold, out[-1].italic, out[-1].size, out[-1].font, out[-1].superscript, out[-1].link) == \
                (r.bold, r.italic, r.size, r.font, r.superscript, r.link):
            out[-1].text += r.text
        else:
            out.append(r)
    return out


def _border_visible(el) -> bool:
    return el is not None and el.get(_w("val")) not in (None, "nil", "none")


def _table_borders(tbl_el, styles: _Styles) -> tuple[dict, bool]:
    sides = ("top", "bottom", "left", "right", "insideH", "insideV")
    vis = {s: False for s in sides}
    tblpr = tbl_el.find(_w("tblPr"))
    sts = tblpr.find(_w("tblStyle")) if tblpr is not None else None
    sources = []
    if sts is not None:
        sources += [s["tblpr"] for s in reversed(styles.chain(sts.get(_w("val"))))]
    sources.append(tblpr)
    for tp in sources:                              # estilo-base primeiro, direto por último
        if tp is None:
            continue
        tb = tp.find(_w("tblBorders"))
        if tb is None:
            continue
        for s in sides:
            el = tb.find(_w(s))
            if el is not None:
                vis[s] = _border_visible(el)
    # bordas por célula
    rows = tbl_el.findall(_w("tr"))
    cell_vertical = cell_inner_h = shaded = False
    for ri, tr in enumerate(rows):
        for tc in tr.findall(_w("tc")):
            tcpr = tc.find(_w("tcPr"))
            if tcpr is None:
                continue
            tcb = tcpr.find(_w("tcBorders"))
            if tcb is not None:
                if _border_visible(tcb.find(_w("left"))) or _border_visible(tcb.find(_w("right"))):
                    cell_vertical = True
                inner_row = 0 < ri < len(rows) - 1
                if inner_row and (_border_visible(tcb.find(_w("top"))) or _border_visible(tcb.find(_w("bottom")))):
                    cell_inner_h = True
            shd = tcpr.find(_w("shd"))
            if shd is not None and (shd.get(_w("fill")) or "auto").lower() not in ("auto", "ffffff", "none"):
                shaded = True
    vis["cell_vertical"] = cell_vertical
    vis["cell_inner_h"] = cell_inner_h
    return vis, shaded


def _load_docx(path: Path) -> Document:
    import docx

    d = docx.Document(str(path))
    styles = _Styles(d, _theme_fonts(path))
    paragraphs: list[Para] = []
    tables: list[TableInfo] = []
    images: list[ImageInfo] = []

    def build_para(p_el, in_table=False, table_index=None) -> Para:
        ps = p_el.find(f"{_w('pPr')}/{_w('pStyle')}")
        sid = ps.get(_w("val")) if ps is not None else styles.default_para
        chain = styles.chain(sid)
        runs, spans, offset = [], [], 0
        in_field_link, collecting, instr = False, False, ""
        for r_el in p_el.iter(_w("r")):
            for ch in r_el:                                   # campos HYPERLINK complexos
                t = _local(ch.tag)
                if t == "fldChar":
                    ty = ch.get(_w("fldCharType"))
                    if ty == "begin":
                        collecting, instr = True, ""
                    elif ty == "separate":
                        in_field_link = "HYPERLINK" in instr.upper()
                        collecting = False
                    elif ty == "end":
                        in_field_link = collecting = False
                elif t == "instrText" and collecting:
                    instr += ch.text or ""
            if _skip_run(r_el, p_el):
                continue
            txt = _run_text(r_el)
            if not txt:
                continue
            run = styles.run_props(r_el, chain)
            run.text = txt
            run.link = in_field_link or _in_link(r_el, p_el)
            runs.append(run)
            spans.append((offset, offset + len(txt), r_el))
            offset += len(txt)
        align, ls, sb, sa, numbered = styles.para_props(p_el, chain)
        first_ind, left_ind = styles.indent_props(p_el, chain)

        # imagens (figuras) neste parágrafo
        n_img = 0
        for dr in p_el.iter(_w("drawing")):
            if _skip_run(dr, p_el):
                continue
            blip = next((e for e in dr.iter(f"{{{A_NS}}}blip")), None)
            chart = next((e for e in dr.iter(f"{{{C_NS}}}chart")), None)
            if blip is None and chart is None:
                continue
            n_img += 1
            info = ImageInfo(para_index=len(paragraphs), kind="picture" if blip is not None else "chart")
            ext = next((e for e in dr.iter(f"{{{WP_NS}}}extent")), None)
            if ext is not None and ext.get("cx"):
                info.width_in = int(ext.get("cx")) / 914400
            if blip is not None:
                rid = blip.get(f"{{{R_NS}}}embed")
                try:
                    from docx.image.image import Image as _Img
                    img = _Img.from_blob(d.part.related_parts[rid].blob)
                    info.px = (img.px_width, img.px_height)
                    if info.width_in:
                        info.dpi = img.px_width / info.width_in
                except Exception:
                    pass
            images.append(info)
        for pict in p_el.iter(_w("pict")):
            if not _skip_run(pict, p_el):
                n_img += 1
                images.append(ImageInfo(para_index=len(paragraphs)))

        return Para(runs=_merge_runs(runs), index=len(paragraphs), style=sid or "",
                    align=align, line_spacing=ls, space_before=sb, space_after=sa,
                    in_table=in_table, table_index=table_index, n_images=n_img,
                    numbered=numbered, first_indent=first_ind, left_indent=left_ind, el=p_el, spans=spans)

    for block in _iter_blocks(d.element.body):
        if _local(block.tag) == "p":
            paragraphs.append(build_para(block))
        else:
            ti = len(tables)
            first = len(paragraphs)
            rows = []
            for tr in block.findall(_w("tr")):
                cells = []
                for tc in tr.findall(_w("tc")):
                    cells.append(" ".join("".join(_run_text(r) for r in p.iter(_w("r"))).strip()
                                          for p in tc.findall(_w("p"))).strip())
                rows.append(cells)
            for p_el in block.iter(_w("p")):
                paragraphs.append(build_para(p_el, True, ti))
            borders, shaded = _table_borders(block, styles)
            tables.append(TableInfo(ti, rows, first, len(paragraphs) - 1, borders, shaded))

    cp = d.core_properties
    props = {"author": cp.author or "", "last_modified_by": cp.last_modified_by or "",
             "title": cp.title or "", "creator": "", "company": "", "manager": ""}
    pages = None
    try:
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(path) as zf:
            if "docProps/app.xml" in zf.namelist():
                root = ET.fromstring(zf.read("docProps/app.xml"))
                for el in root:
                    n = _local(el.tag).lower()
                    if n == "company":
                        props["company"] = (el.text or "").strip()
                    elif n == "manager":
                        props["manager"] = (el.text or "").strip()
                    elif n == "pages" and el.text and el.text.isdigit():
                        pages = int(el.text)
    except Exception:
        pass

    return Document(path=path, fmt="docx", paragraphs=paragraphs, tables=tables,
                    images=images, props=props, size_bytes=path.stat().st_size,
                    pages=pages, exact=True, docx_obj=d)


# ----------------------------------------------------------------------------
def load_document(path) -> Document:
    """A RECI só aceita manuscritos em Word: apenas .docx é lido."""
    path = Path(path)
    if path.suffix.lower() != ".docx":
        raise ValueError(f"Formato não suportado: {path.suffix} — a RECI aceita somente manuscritos em Word (.docx)")
    return _load_docx(path)
