"""TABELAS e FIGURAS (gráficos, mapas etc.) — legendas, linhas, N (%), siglas, total, menções no texto, qualidade e cor."""
import io
import re

from common import Ctx, fmt_list, has_uf, is_simple, note, res, sizes_ok
from structure import BODY_KEYS

CAP = re.compile(r"^\s*(Tabela|Quadro|Figura|Gr[aá]fico)\s*(\d+)\s*(?:[.\-–:]|\t)", re.IGNORECASE)
KIND = {"tabela": "tabela", "quadro": "tabela", "figura": "figura", "grafico": "gráfico", "gráfico": "gráfico"}
MENTION = re.compile(r"\b(Tabelas?|Quadros?|Figuras?|Gr[aá]ficos?)\s+(\d+(?:\s*(?:,|e|a|-|–)\s*\d+)*)", re.IGNORECASE)


def captions(ctx: Ctx):
    """[(tipo, número, Para)] — legendas fora de tabelas, em ordem de aparição."""
    def build():
        out = []
        for p in ctx.doc.body:
            m = CAP.match(p.stripped)
            if m and len(p.stripped.split()) <= 80:
                out.append((KIND[m.group(1).lower()], int(m.group(2)), p))
        return out
    return ctx.memo("captions", build)


def _caption_issues(p):
    issues = []
    if p.align in ("center", "right", "justify"):
        issues.append(f"alinhamento {p.align} (esperado à esquerda)")
    sizes = {r.size for r in p.visible_runs() if r.size and not r.superscript}
    if sizes and not sizes_ok(sizes, 10):
        issues.append(f"fonte {'/'.join(f'{s:g}' for s in sorted(sizes))}pt (esperado 10pt)")
    if is_simple(p) is False:
        issues.append(f"espaçamento entre linhas {p.line_spacing:g} (esperado simples)")
    return issues


def _first_para(ctx, t):
    return ctx.doc.paragraphs[t.first_para]


# ----------------------------- TABELAS ---------------------------------------------------------
def item_tb_max5(ctx: Ctx):
    desc = "Apresenta no máximo 5 figuras e/ou tabelas, apresentadas no corpo do texto"
    nt, ni = len(ctx.doc.tables), len(ctx.doc.images)
    ncap = len(captions(ctx))
    total = max(nt + ni, ncap)
    msg = f"{nt} tabela(s) e {ni} imagem(ns); {ncap} legenda(s) de tabela/figura/gráfico (total {total})"
    notes, probs = [], []
    if total > 5:
        probs.append(f"{total - 5} ilustração(ões) além do limite de 5")
        notes.append(note(captions(ctx)[5][2] if len(captions(ctx)) > 5 else None, f"O manuscrito tem {total} tabelas/figuras; o máximo é 5. Reduza/une ilustrações."))
    ref_h = ctx.sections.heading.get("REFERENCES")
    after = [p for _, _, p in captions(ctx) if ref_h is not None and p.index > ref_h.index]
    if after:
        probs.append("há tabelas/figuras após as Referências (devem estar no corpo do texto)")
        notes += [note(p, "Tabelas e figuras devem estar no corpo do texto, não após as Referências.") for p in after[:2]]
    return res("tb.max5", desc, "NA" if probs else "A", msg + ("; " + "; ".join(probs) if probs else ""), notes)


def _images_after_table_captions(ctx):
    paras = ctx.doc.paragraphs
    hits = []
    for kind, n, p in captions(ctx):
        if kind != "tabela":
            continue
        for q in paras[p.index + 1:p.index + 4]:
            if q.n_images:
                hits.append((n, p))
                break
            if q.stripped:
                break
    return hits


def item_tb_editaveis(ctx: Ctx):
    desc = "Tabelas são editáveis? Estão numeradas em ordem sequencial? Transmitem os dados de forma clara?"
    caps = [(n, p) for k, n, p in captions(ctx) if k == "tabela"]
    if not ctx.doc.tables and not caps:
        return res("tb.editaveis", desc, "NSA", "O manuscrito não contém tabelas")
    msgs, notes = [], []
    nums = [n for n, _ in caps]
    if nums and nums != list(range(1, len(nums) + 1)):
        msgs.append(f"tabelas numeradas {nums} (esperado {list(range(1, len(nums) + 1))})")
        notes += [note(p, f"Numeração fora de ordem: renumere as tabelas em sequência (esperado Tabela {i}).") for i, (n, p) in enumerate(caps, 1) if n != i][:3]
    if caps and not ctx.doc.tables:
        msgs.append("há legendas de tabela, mas nenhuma tabela editável no arquivo")
        notes.append(note(caps[0][1], "Não há tabela editável associada a esta legenda: elabore a tabela no Word."))
    if msgs:
        return res("tb.editaveis", desc, "NA" if not ctx.doc.tables else "AP", "; ".join(msgs), notes)
    return res("tb.editaveis", desc, "A", f"{len(ctx.doc.tables)} tabela(s) editável(is), numeradas em sequência. Clareza dos dados deve ser avaliada manualmente.")


def item_tb_titulo(ctx: Ctx):
    desc = "Tabelas tituladas em cima, alinhadas à esquerda, fonte tamanho 10 e espaçamento simples"
    doc = ctx.doc
    probs, notes = [], []
    if not doc.tables:
        if any(k == "tabela" for k, _, _ in captions(ctx)):
            return res("tb.titulo", desc, "-", "Legendas sem tabela editável: não foi possível verificar a posição")
        return res("tb.titulo", desc, "NSA", "O manuscrito não contém tabelas")
    for t in doc.tables:
        i = t.first_para - 1
        while i >= 0 and not doc.paragraphs[i].stripped:
            i -= 1
        prev = doc.paragraphs[i] if i >= 0 else None
        if prev is not None and not prev.in_table and (m := CAP.match(prev.stripped)) and KIND[m.group(1).lower()] == "tabela":
            iss = _caption_issues(prev)
            if iss:
                probs.append(f"Tabela {m.group(2)}: " + ", ".join(iss))
                notes.append(note(prev, "Legenda de tabela: " + ", ".join(iss) + "."))
            continue
        j = t.last_para + 1
        while j < len(doc.paragraphs) and not doc.paragraphs[j].stripped:
            j += 1
        nxt = doc.paragraphs[j] if j < len(doc.paragraphs) else None
        if nxt is not None and CAP.match(nxt.stripped) and KIND[CAP.match(nxt.stripped).group(1).lower()] == "tabela":
            probs.append(f"Tabela {t.index + 1}: legenda abaixo da tabela (deve estar acima)")
            notes.append(note(nxt, "A legenda da tabela deve estar acima da tabela."))
        else:
            probs.append(f"Tabela {t.index + 1}: legenda não encontrada")
            notes.append(note(_first_para(ctx, t), "Esta tabela não tem legenda acima (ex.: “Tabela 1. Título explicativo, local, ano.”)."))
    return res("tb.titulo", desc, "NA" if probs else "A", "; ".join(probs) if probs else f"{len(doc.tables)} tabela(s) com legenda acima, à esquerda, fonte 10 e espaçamento simples", notes)


def _mentions_item(ctx: Ctx, item_id: str, kinds: tuple, label: str, example: str):
    desc = f"As {label} não devem ser citadas ao longo do texto, apenas no final do parágrafo entre parênteses. Ex.: {example}"
    cap_ids = {id(p) for _, _, p in captions(ctx)}
    probs_a, probs_b, notes, total = [], [], [], 0
    for k in BODY_KEYS:
        for p in ctx.sections.get(k):
            if id(p) in cap_ids:
                continue
            t = p.text
            for m in MENTION.finditer(t):
                if KIND[m.group(1).lower().rstrip("s")] not in kinds:
                    continue
                total += 1
                open_i = t.rfind("(", 0, m.start())
                close_i = t.find(")", m.end())
                inside = open_i != -1 and close_i != -1 and ")" not in t[open_i:m.start()]
                if not inside:
                    probs_a.append(f"{m.group(0)} ({ctx.where(p)})")
                    notes.append(note(p, f"Não cite {label} ao longo do texto: mencione apenas no final do parágrafo, entre parênteses (ex.: “...resultado. ({example.split('(')[-1].rstrip(').')}).”).", m.start(), m.end()))
                elif t[close_i + 1:].strip() not in ("", ".", ". "):
                    probs_b.append(f"{m.group(0)} ({ctx.where(p)})")
                    notes.append(note(p, "A menção deve ficar entre parênteses no final do parágrafo.", open_i, close_i + 1))
    if total == 0:
        return res(item_id, desc, "NSA" if not any(k in kinds for k, _, _ in captions(ctx)) else "-", f"Nenhuma menção a {label} no texto")
    if probs_a:
        return res(item_id, desc, "NA" if len(probs_a) > total / 2 else "AP", f"{len(probs_a)} menção(ões) fora de parênteses: " + fmt_list(probs_a, 3) + (f"; {len(probs_b)} fora do final do parágrafo" if probs_b else ""), notes[:10])
    if probs_b:
        return res(item_id, desc, "AP", f"{len(probs_b)} menção(ões) entre parênteses, mas fora do final do parágrafo: " + fmt_list(probs_b, 3), notes[:10])
    return res(item_id, desc, "A", f"{total} menção(ões) entre parênteses no final do parágrafo")


def item_tb_citacao(ctx): return _mentions_item(ctx, "tb.citacao", ("tabela",), "tabelas", "Texto……… (Tabela 1).")
def item_fi_citacao(ctx): return _mentions_item(ctx, "fi.citacao", ("figura", "gráfico"), "figuras", "Texto……… (Figura 1).")


def item_tb_linhas(ctx: Ctx):
    desc = "Nas tabelas não há linhas entre as variáveis nem linhas de fundo e o espaçamento entre as variáveis é simples"
    if not ctx.doc.tables:
        return res("tb.linhas", desc, "NSA", "O manuscrito não contém tabelas")
    probs, notes = [], []
    for t in ctx.doc.tables:
        b, why = t.borders or {}, []
        if b.get("insideV") or b.get("left") or b.get("right") or b.get("cell_vertical"):
            why.append("linhas verticais")
        if b.get("insideH") or b.get("cell_inner_h"):
            why.append("linhas entre as variáveis")
        if t.shaded:
            why.append("sombreamento de fundo")
        cells = [p for p in ctx.doc.paragraphs[t.first_para:t.last_para + 1] if p.stripped]
        bad = [p for p in cells if is_simple(p) is False or (p.space_after or 0) > 0.5]
        if bad:
            why.append(f"espaçamento entre variáveis não simples ({bad[0].line_spacing:g}/após {bad[0].space_after:g}pt)")
        if why:
            probs.append(f"Tabela {t.index + 1}: " + ", ".join(why))
            notes.append(note(_first_para(ctx, t), f"Tabela {t.index + 1}: " + ", ".join(why) + ". Mantenha apenas as linhas de topo, cabeçalho e rodapé, sem fundo e com espaçamento simples."))
    return res("tb.linhas", desc, "NA" if probs else "A", "; ".join(probs) if probs else "Tabelas sem linhas internas/laterais, sem fundo e com espaçamento simples", notes)


def item_tb_word(ctx: Ctx):
    desc = "Tabelas são elaboradas no Word"
    img = _images_after_table_captions(ctx)
    as_fig = [(n, p) for k, n, p in captions(ctx) if k == "figura" and re.match(r"^\s*Figura\s*\d+\s*[.\-–:]?\s*(Tabela|Quadro)\b", p.stripped, re.IGNORECASE)]
    bad = img + as_fig
    if bad:
        return res("tb.word", desc, "NA", "Tabela(s) inserida(s) como imagem: " + ", ".join(f"{n} ({ctx.where(p)})" for n, p in bad) + " — refaça no Word como tabela editável",
                   [note(p, "Esta tabela está como imagem: refaça no Word (Inserir > Tabela).") for _, p in bad])
    if not ctx.doc.tables and not any(k == "tabela" for k, _, _ in captions(ctx)):
        return res("tb.word", desc, "NSA", "O manuscrito não contém tabelas")
    return res("tb.word", desc, "A", f"{len(ctx.doc.tables)} tabela(s) elaborada(s) no Word")


def item_tb_n_pct(ctx: Ctx):
    desc = "Tabelas com N e % na mesma coluna, N (%), sem o símbolo “%” nos dados. Ex.: N (%) → 10 (100)"
    if not ctx.doc.tables:
        return res("tb.n_pct", desc, "NSA", "O manuscrito não contém tabelas")
    probs, notes = [], []
    for t in ctx.doc.tables:
        why = []
        header = [c.strip().lower() for c in t.rows[0]] if t.rows else []
        if any(c in ("%", "percentual", "percentagem", "(%)") for c in header):
            why.append("N e % em colunas separadas")
        pct = [c for r in t.rows[1:] for c in r if "%" in c]
        if pct:
            why.append(f"símbolo % nos dados (ex.: “{pct[0][:20]}”)")
        if why:
            probs.append(f"Tabela {t.index + 1}: " + ", ".join(why))
            notes.append(note(_first_para(ctx, t), f"Tabela {t.index + 1}: " + ", ".join(why) + ". Use uma só coluna “N (%)” com valores como 10 (100), sem o símbolo %."))
    return res("tb.n_pct", desc, "NA" if probs else "A", "; ".join(probs) if probs else "N e % na mesma coluna, sem o símbolo % nos dados", notes)


_ACR_CELL = re.compile(r"(?<![\wÀ-ÿ])([A-ZÀ-Ú]{2,8})(?![\wÀ-ÿ])")
_LEGEND = re.compile(r"^\s*(siglas?|legenda|abreviaturas?|abrevia[çc][õo]es|notas?|fonte)\b|\b[A-ZÀ-Ú]{2,8}\s*[:=]", re.IGNORECASE)


def item_tb_siglas(ctx: Ctx):
    desc = "As siglas devem ser escritas embaixo da tabela, com fonte tamanho 10 e espaçamento simples"
    doc = ctx.doc
    if not doc.tables:
        return res("tb.siglas", desc, "NSA", "O manuscrito não contém tabelas")
    probs, notes, checked = [], [], 0
    for t in doc.tables:
        acr = sorted({a for r in t.rows for c in r for a in _ACR_CELL.findall(c) if a not in ("N",)})
        if not acr:
            continue
        checked += 1
        j = t.last_para + 1
        while j < len(doc.paragraphs) and not doc.paragraphs[j].stripped:
            j += 1
        nxt = doc.paragraphs[j] if j < len(doc.paragraphs) else None
        if nxt is None or not _LEGEND.search(nxt.stripped) or CAP.match(nxt.stripped):
            probs.append(f"Tabela {t.index + 1}: siglas ({fmt_list(acr, 4, ', ')}) sem legenda abaixo da tabela")
            notes.append(note(_first_para(ctx, t), f"Tabela {t.index + 1}: escreva embaixo da tabela o significado das siglas ({fmt_list(acr, 4, ', ')}), fonte 10 e espaçamento simples."))
            continue
        iss = []
        sizes = {r.size for r in nxt.visible_runs() if r.size}
        if sizes and not sizes_ok(sizes, 10):
            iss.append(f"fonte {'/'.join(f'{s:g}' for s in sorted(sizes))}pt (esperado 10pt)")
        if is_simple(nxt) is False:
            iss.append(f"espaçamento {nxt.line_spacing:g} (esperado simples)")
        if iss:
            probs.append(f"Tabela {t.index + 1}: legenda de siglas com " + ", ".join(iss))
            notes.append(note(nxt, "Legenda de siglas: " + ", ".join(iss) + "."))
    if checked == 0:
        return res("tb.siglas", desc, "NSA", "Tabelas sem siglas")
    return res("tb.siglas", desc, "NA" if probs else "A", "; ".join(probs) if probs else "Siglas explicadas abaixo das tabelas, fonte 10 e espaçamento simples", notes)


def item_tb_total(ctx: Ctx):
    desc = "Não deve haver uma linha com o total (somatório) dos dados"
    if not ctx.doc.tables:
        return res("tb.total", desc, "NSA", "O manuscrito não contém tabelas")
    probs, notes = [], []
    for t in ctx.doc.tables:
        for ri, r in enumerate(t.rows[1:], 1):
            if r and re.match(r"^\s*(total|soma|somat[óo]rio|total geral)\b", r[0], re.IGNORECASE):
                probs.append(f"Tabela {t.index + 1}, linha {ri + 1} (“{r[0][:20]}”)")
                notes.append(note(_first_para(ctx, t), f"Tabela {t.index + 1}: remova a linha de total (“{r[0][:20]}”)."))
    return res("tb.total", desc, "NA" if probs else "A", "Linha de total encontrada: " + fmt_list(probs, 3) if probs else "Nenhuma linha de total nas tabelas", notes)


def _explicativo(ctx: Ctx, item_id: str, kinds: tuple, label: str):
    desc = f"Os títulos das {label} apresentam conteúdo explicativo, com recorte geográfico e temporal do estudo"
    caps = [c for c in captions(ctx) if c[0] in kinds]
    if not caps:
        return res(item_id, desc, "NSA", f"Nenhuma legenda de {label} encontrada")
    probs, notes = [], []
    for k, n, p in caps:
        t, miss = p.stripped, []
        if not re.search(r"\b(19|20)\d{2}\b", t):
            miss.append("recorte temporal")
        if not (has_uf(t) or re.search(r"Brasil|Brazil|Am[ée]rica|Regi[ãa]o|Mundo|munic[ií]pio", t, re.IGNORECASE)):
            miss.append("recorte geográfico")
        if len(t.split()) < 8:
            miss.append("conteúdo explicativo (título curto)")
        if miss:
            probs.append(f"{k.capitalize()} {n}: falta " + " e ".join(miss))
            notes.append(note(p, f"Legenda sem {' e '.join(miss)}. Ex.: “Tabela 1. Distribuição ..., Curitiba, Paraná, 2020.”"))
    if not probs:
        return res(item_id, desc, "A", "Legendas com conteúdo explicativo, local e período")
    return res(item_id, desc, "NA" if len(probs) == len(caps) else "AP", "; ".join(probs), notes)


def item_tb_explicativo(ctx): return _explicativo(ctx, "tb.explicativo", ("tabela",), "tabelas")
def item_fi_explicativo(ctx): return _explicativo(ctx, "fi.explicativo", ("figura", "gráfico"), "figuras")


# ----------------------------- FIGURAS ---------------------------------------------------------
def _image_captions(ctx):
    caps = [c for c in captions(ctx) if c[0] in ("figura", "gráfico")]
    paras = ctx.doc.paragraphs
    out = []
    for im in ctx.doc.images:
        if paras[im.para_index].in_table:
            continue
        below = next((c for c in caps if 0 <= c[2].index - im.para_index <= 6), None)
        above = next((c for c in reversed(caps) if 0 < im.para_index - c[2].index <= 3), None)
        out.append((im, below, above))
    return out


def item_fi_qualidade(ctx: Ctx):
    desc = "Figuras apresentam boa qualidade? Estão numeradas em ordem sequencial?"
    caps = captions(ctx)
    ims = [i for i in ctx.doc.images if i.kind == "picture"]
    figcaps = [(k, n, p) for k, n, p in caps if k in ("figura", "gráfico")]
    if not ims and not figcaps and not ctx.doc.images:
        return res("fi.qualidade", desc, "NSA", "O manuscrito não contém figuras")
    msgs, notes, bad = [], [], False
    for kind in ("figura", "gráfico"):
        nums = [n for k, n, _ in figcaps if k == kind]
        if nums and nums != list(range(1, len(nums) + 1)):
            bad = True
            msgs.append(f"{kind}s numeradas {nums} (esperado {list(range(1, len(nums) + 1))})")
            notes += [note(p, f"Numeração fora de ordem: renumere em sequência ({kind} {i}).") for i, (k, n, p) in enumerate([c for c in figcaps if c[0] == kind], 1) if n != i][:3]
    known = [i for i in ims if i.dpi]
    low = [i for i in known if i.dpi < 96]
    mid = [i for i in known if 96 <= i.dpi < 150]
    paras = ctx.doc.paragraphs
    if low:
        bad = True
        msgs.append(f"{len(low)} imagem(ns) com resolução baixa (<96 dpi efetivos)")
        notes += [note(paras[i.para_index], f"Imagem com resolução baixa (~{i.dpi:.0f} dpi): use figura de melhor qualidade (≥300 dpi).") for i in low]
    elif mid:
        msgs.append(f"{len(mid)} imagem(ns) entre 96 e 150 dpi")
        notes += [note(paras[i.para_index], f"Resolução mediana (~{i.dpi:.0f} dpi): prefira ≥300 dpi.") for i in mid]
    if not msgs:
        return res("fi.qualidade", desc, "A", ("DPI efetivos: " + ", ".join(f"{i.dpi:.0f}" for i in known) + ". ") + "Figuras numeradas em sequência; nitidez deve ser conferida visualmente.")
    return res("fi.qualidade", desc, "NA" if (low and not mid and len(low) == len(known)) or (bad and not low) else "AP", "; ".join(msgs), notes)


def item_fi_titulo(ctx: Ctx):
    desc = "Figuras tituladas embaixo, alinhadas à esquerda, tamanho 10 e com espaçamento simples (exemplo: gráficos e mapas)"
    probs, notes, n = [], [], 0
    for k, (im, below, above) in enumerate(_image_captions(ctx), 1):
        cap = below or above
        if cap and cap[0] == "gráfico":
            continue
        n += 1
        if below:
            iss = _caption_issues(below[2])
            if iss:
                probs.append(f"Figura {below[1]}: " + ", ".join(iss))
                notes.append(note(below[2], "Legenda de figura: " + ", ".join(iss) + "."))
        elif above:
            probs.append(f"Figura {above[1]}: legenda acima da imagem (deve estar abaixo)")
            notes.append(note(above[2], "A legenda da figura deve estar abaixo da imagem."))
        else:
            probs.append(f"Imagem {k}: legenda não encontrada")
            notes.append(note(ctx.doc.paragraphs[im.para_index], "Esta figura não tem legenda abaixo (ex.: “Figura 1. Título explicativo, local, ano.”)."))
    if n == 0:
        return res("fi.titulo", desc, "NSA", "Nenhuma figura encontrada")
    return res("fi.titulo", desc, "NA" if probs else "A", "; ".join(probs) if probs else f"{n} figura(s) com legenda abaixo, à esquerda, fonte 10 e espaçamento simples", notes)


def item_fi_centralizada(ctx: Ctx):
    desc = "A ilustração deve estar centralizada no texto"
    ims = [im for im in ctx.doc.images if not ctx.doc.paragraphs[im.para_index].in_table]
    if not ims:
        return res("fi.centralizada", desc, "NSA", "O manuscrito não contém figuras")
    bad = [ctx.doc.paragraphs[im.para_index] for im in ims if ctx.doc.paragraphs[im.para_index].align != "center"]
    notes = [note(p, "Centralize esta ilustração no texto.") for p in bad]
    return res("fi.centralizada", desc, "NA" if bad else "A", (f"{len(bad)}/{len(ims)} ilustração(ões) não centralizada(s), a partir de {ctx.where(bad[0])}") if bad else f"{len(ims)} ilustração(ões) centralizada(s)", notes)


def _blue_share(blob: bytes):
    """(fração de pixels coloridos, fração azul entre eles) ou None."""
    try:
        import colorsys

        from PIL import Image
        im = Image.open(io.BytesIO(blob)).convert("RGB").resize((64, 64))
    except Exception:
        return None
    colored = blue = 0
    for r, g, b in im.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s > 0.25 and 0.2 < v:
            colored += 1
            if 0.5 <= h <= 0.72:           # 180°–260°
                blue += 1
    return colored / 4096, (blue / colored if colored else 1.0)


def _blob_of(ctx, para):
    ns_a = "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
    ns_r = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
    for blip in para.el.iter(ns_a):
        try:
            return ctx.doc.docx_obj.part.related_parts[blip.get(ns_r)].blob
        except Exception:
            return None
    return None


def item_fi_cor(ctx: Ctx):
    desc = "Gráficos estão padronizados preferencialmente em cores em tom azul"
    graphs = [(n, p) for k, n, p in captions(ctx) if k == "gráfico"]
    pics = [(im, below, above) for im, below, above in _image_captions(ctx) if ((below or above) and (below or above)[0] == "gráfico")]
    if not graphs and not pics:
        return res("fi.cor", desc, "NSA", "O manuscrito não contém gráficos")
    notes, msgs, unknown = [], [], 0
    for im, below, above in pics:
        p = ctx.doc.paragraphs[im.para_index]
        blob = _blob_of(ctx, p) if im.kind == "picture" else None
        r = _blue_share(blob) if blob else None
        if r is None:
            unknown += 1
            continue
        colored, blue = r
        if colored > 0.03 and blue < 0.6:
            n = (below or above)[1]
            msgs.append(f"Gráfico {n}: predominam cores fora do tom azul ({blue:.0%} azul entre os pixels coloridos)")
            notes.append(note(p, f"Gráfico {n}: padronize as cores preferencialmente em tons de azul."))
    if msgs:
        return res("fi.cor", desc, "AP", "; ".join(msgs), notes)
    if unknown and unknown == len(pics):
        return res("fi.cor", desc, "-", "Cores não puderam ser analisadas automaticamente: conferir se os gráficos estão em tom azul")
    return res("fi.cor", desc, "A", "Gráficos em tons de azul/neutros (análise automática por amostragem de pixels)")


def item_fi_graf_titulo(ctx: Ctx):
    desc = "Gráficos estão titulados embaixo, alinhados à esquerda, fonte no tamanho 10 e com espaçamentos simples"
    caps = [c for c in captions(ctx) if c[0] == "gráfico"]
    if not caps:
        return res("fi.graf_titulo", desc, "NSA", "O manuscrito não contém gráficos (legendas “Gráfico N”)")
    probs, notes = [], []
    ims = [i.para_index for i in ctx.doc.images]
    for _, n, p in caps:
        after = any(0 < i - p.index <= 4 for i in ims)
        before = any(0 < p.index - i <= 4 for i in ims)
        iss = _caption_issues(p)
        if after and not before:
            iss.insert(0, "legenda acima do gráfico (deve estar abaixo)")
        if iss:
            probs.append(f"Gráfico {n}: " + ", ".join(iss))
            notes.append(note(p, f"Gráfico {n}: " + ", ".join(iss) + "."))
    return res("fi.graf_titulo", desc, "NA" if probs else "A", "; ".join(probs) if probs else f"{len(caps)} gráfico(s) com legenda correta", notes)


# ----------------------------- RESULTADOS ---------------------------------------------------------
def _expand(s):
    nums = set()
    for part in re.split(r"\s*(?:,|e)\s*", s):
        m = re.match(r"(\d+)\s*(?:a|-|–)\s*(\d+)$", part.strip())
        if m:
            nums.update(range(int(m.group(1)), int(m.group(2)) + 1))
        elif part.strip().isdigit():
            nums.add(int(part))
    return nums


def item_rs_ilustracoes(ctx: Ctx):
    desc = "Apresenta tabelas e ilustrações em sequência lógica, com texto complementar a essas (no máximo 5 ilustrações)"
    caps = captions(ctx)
    if not caps:
        return res("rs.ilustracoes", desc, "NSA", "Nenhuma legenda de tabela/figura/gráfico encontrada")
    cap_ids = {id(p) for _, _, p in caps}
    text = "\n".join(p.text for k in BODY_KEYS for p in ctx.sections.get(k) if id(p) not in cap_ids)
    cited = {"tabela": set(), "figura": set(), "gráfico": set()}
    for m in MENTION.finditer(text):
        cited[KIND[m.group(1).lower().rstrip("s")]].update(_expand(m.group(2)))
    missing = [(k, n, p) for k, n, p in caps if n not in cited[k]]
    msgs, notes = [], []
    if missing:
        msgs.append("não citadas no texto: " + ", ".join(f"{k} {n} ({ctx.where(p)})" for k, n, p in missing))
        notes += [note(p, f"{k.capitalize()} {n} não é mencionada no texto: acrescente texto complementar com a menção “({k.capitalize()} {n}).”.") for k, n, p in missing]
    if len(caps) > 5:
        msgs.append(f"{len(caps)} ilustrações (máximo 5)")
    return res("rs.ilustracoes", desc, "NA" if msgs else "A", "; ".join(msgs) if msgs else "Todas as tabelas/figuras são citadas no texto (ordem lógica deve ser avaliada manualmente)", notes)
