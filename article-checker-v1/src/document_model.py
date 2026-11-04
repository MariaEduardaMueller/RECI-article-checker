"""
Modelo de documento unificado (.docx e .pdf).

Todas as verificações do reci-checker trabalham sobre `Document`, de modo que a
mesma regra do Checklist vale para os dois formatos.

 * .docx -> leitura exata via XML (estilos, herança de formatação, espaçamento,
            bordas de tabelas, resolução de imagens...).
 * .pdf  -> leitura via pdfplumber; fontes/negrito/itálico/sobrescrito são
            exatos, mas alinhamento, espaçamento e parágrafos são ESTIMADOS a
            partir da geometria das linhas (`Document.exact == False`).

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
    line_runs: list | None = None        # PDF: runs de cada linha visual

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
                    lines[-1].append(Run(part, r.bold, r.italic, r.size, r.font, r.superscript))
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
    exact: bool = True                   # False => layout estimado (PDF)

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
        if out and (out[-1].bold, out[-1].italic, out[-1].size, out[-1].font, out[-1].superscript) == \
                (r.bold, r.italic, r.size, r.font, r.superscript):
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
        runs = []
        for r_el in p_el.iter(_w("r")):
            if _skip_run(r_el, p_el):
                continue
            txt = _run_text(r_el)
            if not txt:
                continue
            run = styles.run_props(r_el, chain)
            run.text = txt
            runs.append(run)
        align, ls, sb, sa, numbered = styles.para_props(p_el, chain)

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
                    numbered=numbered)

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
                    pages=pages, exact=True)


# ----------------------------------------------------------------------------
# PDF
# ----------------------------------------------------------------------------
_NATURAL_LEADING = {"times": 1.15, "liberation": 1.11, "arial": 1.15, "helvetica": 1.15,
                    "calibri": 1.22, "cambria": 1.17, "georgia": 1.14, "verdana": 1.22}


def _font_flags(fontname: str) -> tuple[bool, bool]:
    name = fontname.split("+", 1)[-1]
    bold = bool(re.search(r"bold|black|heavy|semibold|demi|(?<![a-z])bd(?![a-z])", name, re.I))
    italic = bool(re.search(r"italic|oblique|(?<![a-z])ital|[-,]it$|(?<![a-z])it(?![a-z])", name, re.I))
    return bold, italic


def _font_family(fontname: str) -> str:
    base = fontname.split("+", 1)[-1]
    low = base.lower().replace("-", "").replace(" ", "")
    if "timesnewroman" in low or low.startswith("times"):
        return "Times New Roman"
    base = re.sub(r"[-,](Bold|Italic|Oblique|BoldItalic|BoldOblique|Regular|Roman)$", "", base, flags=re.I)
    base = re.sub(r"(PSMT|MT|PS)$", "", base)
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base).strip()


def _natural_leading(font: str | None) -> float:
    low = (font or "").lower()
    for k, v in _NATURAL_LEADING.items():
        if k in low:
            return v
    return 1.17


def _pdf_page_lines(page, pno: int) -> list[dict]:
    raw = [c for c in page.chars if c.get("text") and c["text"] != "\x00" and c.get("size")]
    if not raw:
        return []
    seen, chars = set(), []
    for c in raw:                                         # remove caracteres duplicados (falso negrito)
        k = (c["text"], round(c["x0"], 1), round(c["bottom"], 1))
        if k not in seen:
            seen.add(k)
            chars.append(c)
    med = statistics.median(c["size"] for c in chars)
    tol = 0.6 * med
    chars.sort(key=lambda c: c["bottom"])
    clusters: list[list[dict]] = []
    ref = None
    for c in chars:
        if ref is None or c["bottom"] - ref > tol:
            clusters.append([c])
            ref = c["bottom"]
        else:
            clusters[-1].append(c)
            ref = max(ref, c["bottom"]) if c["size"] >= 0.85 * med else ref

    lines = []
    for cl in clusters:
        cl.sort(key=lambda c: c["x0"])
        dom = Counter(round(c["size"], 1) for c in cl if c["text"].strip()).most_common(1)
        if not dom:
            continue
        dom_size = dom[0][0]
        base_cands = [round(c["bottom"], 0) for c in cl if c["size"] >= 0.85 * dom_size and c["text"].strip()]
        baseline = Counter(base_cands).most_common(1)[0][0] if base_cands else cl[0]["bottom"]

        items = []                                       # (texto, fonte, tamanho, sup)
        prev = None
        first_word_w = None
        for c in cl:
            t = c["text"]
            sup = c["size"] < 0.8 * dom_size and c["bottom"] <= baseline - 0.12 * dom_size and t.strip() != ""
            if prev is not None and t.strip() != "" and prev["text"].strip() != "":
                gap = c["x0"] - prev["x1"]
                if gap > 0.17 * max(c["size"], prev["size"]):
                    items.append((" ", prev["fontname"], prev["size"], False))
                    if first_word_w is None:
                        first_word_w = prev["x1"] - cl[0]["x0"]
            elif prev is not None and t.strip() == "" and first_word_w is None and prev["text"].strip() != "":
                first_word_w = prev["x1"] - cl[0]["x0"]
            items.append((t, c["fontname"], c["size"], sup))
            prev = c
        if first_word_w is None:
            first_word_w = cl[-1]["x1"] - cl[0]["x0"]

        runs: list[Run] = []
        for t, fn, sz, sup in items:
            b, i = _font_flags(fn)
            r = Run(t, b, i, round(sz, 1), _font_family(fn), sup)
            if runs and (runs[-1].bold, runs[-1].italic, runs[-1].size, runs[-1].font, runs[-1].superscript) == \
                    (r.bold, r.italic, r.size, r.font, r.superscript):
                runs[-1].text += t
            else:
                runs.append(r)
        text = "".join(r.text for r in runs).strip()
        if not text:
            continue
        vis = [r for r in runs if r.text.strip()]
        lines.append({
            "page": pno, "x0": cl[0]["x0"], "x1": max(c["x1"] for c in cl),
            "bottom": baseline, "top": min(c["top"] for c in cl), "size": dom_size,
            "runs": runs, "text": text, "first_word_w": first_word_w,
            "bold_all": all(r.bold for r in vis), "font": vis[0].font if vis else None,
        })
    lines.sort(key=lambda l: l["bottom"])
    return lines


def _percentile(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))]


def _load_pdf(path: Path) -> Document:
    import pdfplumber

    pages_lines: list[list[dict]] = []
    page_imgs: list[list[dict]] = []
    dims = []
    with pdfplumber.open(str(path)) as pdf:
        meta = pdf.metadata or {}
        for pno, page in enumerate(pdf.pages, 1):
            pages_lines.append(_pdf_page_lines(page, pno))
            page_imgs.append([i for i in page.images if (i["x1"] - i["x0"]) > 30 and (i["bottom"] - i["top"]) > 30])
            dims.append((page.width, page.height))
        n_pages = len(pdf.pages)

    # cabeçalhos/rodapés: números de página e textos repetidos
    rep = Counter()
    for pl, (w, h) in zip(pages_lines, dims):
        for l in pl:
            if l["top"] < 0.06 * h or l["bottom"] > 0.93 * h:
                rep[re.sub(r"\d+", "#", l["text"])] += 1
    for k, (pl, (w, h)) in enumerate(zip(pages_lines, dims)):
        keep = []
        for l in pl:
            edge = l["top"] < 0.06 * h or l["bottom"] > 0.93 * h
            if edge and (re.fullmatch(r"[\d\s\-–/pPáaA gina]+", l["text"]) or
                         (n_pages >= 3 and rep[re.sub(r"\d+", "#", l["text"])] >= 3)):
                continue
            keep.append(l)
        pages_lines[k] = keep

    all_lines = [l for pl in pages_lines for l in pl]
    long_lines = [l for l in all_lines if len(l["text"]) >= 50]
    if long_lines:
        left = _percentile([l["x0"] for l in long_lines], 0.15)
        right = max(_percentile([l["x1"] for l in long_lines], 0.92),
                    statistics.median(l["x1"] for l in long_lines))
    elif all_lines:
        left, right = min(l["x0"] for l in all_lines), max(l["x1"] for l in all_lines)
    else:
        left, right = 0, 1
    width = max(right - left, 1)

    diffs = []
    for pl in pages_lines:
        for a, b in zip(pl, pl[1:]):
            d = b["bottom"] - a["bottom"]
            if len(a["text"]) >= 40 and len(b["text"]) >= 40 and abs(a["size"] - b["size"]) < 0.5 \
                    and 0.8 * a["size"] <= d <= 3 * a["size"]:
                diffs.append(d)
    pitch = statistics.median(diffs) if diffs else (statistics.median(l["size"] for l in all_lines) * 1.2 if all_lines else 14)

    # passo local: mediana das distâncias entre linhas vizinhas (±3) na mesma página
    for pl in pages_lines:
        gaps = [b["bottom"] - a["bottom"] for a, b in zip(pl, pl[1:])]
        for k, (a, b) in enumerate(zip(pl, pl[1:])):
            win = [g for g in gaps[max(0, k - 3):k + 4] if 0.8 * a["size"] <= g <= 2.2 * a["size"]]
            b["local_pitch"] = statistics.median(win) if win else pitch

    def line_align(l, page_w):
        center = (l["x0"] + l["x1"]) / 2
        mid = (left + right) / 2
        if abs(center - mid) <= 0.025 * width and l["x0"] - left > 8 and right - l["x1"] > 8:
            return "center"
        if abs(right - l["x1"]) <= 3 and l["x0"] - left > 0.3 * width:
            return "right"
        return "left"

    def new_para(prev, cur) -> bool:
        gap = cur["bottom"] - prev["bottom"]
        if gap > 1.45 * cur.get("local_pitch", pitch):
            return True
        if abs(cur["size"] - prev["size"]) > 0.8:
            return True
        if prev["bold_all"] != cur["bold_all"] and (prev["bold_all"] or cur["bold_all"]):
            return True
        pa, ca = line_align(prev, 0), line_align(cur, 0)
        if (pa == "center") != (ca == "center"):
            return True
        if re.match(r"^\d{1,3}\.\s+\S", cur["text"]):
            return True
        if re.match(r"^\d{1,2}[A-ZÀ-Ú]", cur["text"]) and cur["runs"][0].superscript:
            return True                                   # início de afiliação (número sobrescrito)
        if pa in ("center", "right"):
            # linhas centralizadas/à direita: só continuam na linha seguinte se a anterior estiver praticamente cheia
            if width - (prev["x1"] - prev["x0"]) > 0.2 * width:
                return True
        elif right - prev["x1"] > cur["first_word_w"] + 0.3 * cur["size"]:
            return True
        if ca == "left" and cur["x0"] - left > 0.8 * cur["size"] and prev["x0"] - left < 0.5 * cur["size"]:
            return True
        return False

    paragraphs: list[Para] = []
    images: list[ImageInfo] = []

    def finish(lines_: list[dict], prev_bottom) -> None:
        if not lines_:
            return
        runs: list[Run] = []
        for i, l in enumerate(lines_):
            if i > 0:
                prev_txt = runs[-1].text if runs else ""
                if prev_txt.endswith("-") and l["runs"][0].text[:1].islower():
                    pass
                else:
                    runs[-1].text += " "
            for r in l["runs"]:
                runs.append(Run(r.text, r.bold, r.italic, r.size, r.font, r.superscript))
        aligns = [line_align(l, 0) for l in lines_]
        if all(a == "center" for a in aligns):
            align = "center"
        elif all(a == "right" for a in aligns):
            align = "right"
        elif len(lines_) >= 2:
            full = [l for l in lines_[:-1] if right - l["x1"] <= 0.6 * l["size"] + 2]
            align = "justify" if len(full) >= 0.7 * (len(lines_) - 1) else "left"
        else:
            align = None if right - lines_[0]["x1"] <= 3 else "left"
        ls = None
        if len(lines_) >= 2:
            ds = [b["bottom"] - a["bottom"] for a, b in zip(lines_, lines_[1:])]
            nat = _natural_leading(lines_[0]["font"])
            ls = round((statistics.median(ds) / (lines_[0]["size"] * nat)) * 20) / 20
        sb = None
        if prev_bottom is not None:
            own = statistics.median([b["bottom"] - a["bottom"] for a, b in zip(lines_, lines_[1:])]) if len(lines_) >= 2 else lines_[0].get("local_pitch", pitch)
            extra = (lines_[0]["bottom"] - prev_bottom) - own
            sb = round(extra, 1) if extra > 0.4 * lines_[0]["size"] else 0.0
        runs = _merge_runs(runs)
        for k, r in enumerate(runs):
            r.text = re.sub(r" {2,}", " ", r.text)
            if k and runs[k - 1].text.endswith(" ") and r.text.startswith(" "):
                r.text = r.text[1:]
        paragraphs.append(Para(runs=runs, index=len(paragraphs), align=align,
                               line_spacing=ls, space_before=sb, page=lines_[0]["page"],
                               line_runs=[l["runs"] for l in lines_]))

    cur: list[dict] = []
    prev_bottom = None
    for pno, (pl, imgs) in enumerate(zip(pages_lines, page_imgs), 1):
        items = [("l", l["top"], l) for l in pl] + [("i", im["top"], im) for im in imgs]
        items.sort(key=lambda t: t[1])
        for kind, _, obj in items:
            if kind == "i":
                finish(cur, prev_bottom)
                prev_bottom = cur[-1]["bottom"] if cur else prev_bottom
                cur = []
                info = ImageInfo(para_index=len(paragraphs), kind="picture", page=pno,
                                 width_in=(obj["x1"] - obj["x0"]) / 72)
                src = obj.get("srcsize")
                if src and info.width_in:
                    info.px = (int(src[0]), int(src[1]))
                    info.dpi = src[0] / info.width_in
                images.append(info)
                paragraphs.append(Para(runs=[], index=len(paragraphs), n_images=1, page=pno))
                prev_bottom = obj["bottom"]
                continue
            if cur and new_para(cur[-1], obj):
                finish(cur, prev_bottom)
                prev_bottom = cur[-1]["bottom"]
                cur = []
            cur.append(obj)
    finish(cur, prev_bottom)

    props = {"author": meta.get("Author", "") or "", "last_modified_by": "", "title": meta.get("Title", "") or "",
             "creator": meta.get("Creator", "") or "", "company": "", "manager": ""}
    return Document(path=path, fmt="pdf", paragraphs=paragraphs, tables=[], images=images,
                    props=props, size_bytes=path.stat().st_size, pages=n_pages, exact=False)


# ----------------------------------------------------------------------------
def load_document(path) -> Document:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".docx":
        return _load_docx(path)
    if ext == ".pdf":
        return _load_pdf(path)
    raise ValueError(f"Formato não suportado: {ext} (use .docx ou .pdf)")
