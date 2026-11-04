"""TABELAS, QUADROS E GRÁFICOS — itens 54, 58, 61, 121, 122, 127 a 133."""
import re

from common import Ctx, fmt_list, has_uf, is_simple, res, sizes_ok
from structure import BODY_KEYS

CAP = re.compile(r"^\s*(Tabela|Quadro|Figura|Gr[aá]fico)\s*(\d+)\s*(?:[.\-–:]|\t)", re.IGNORECASE)
KIND = {"tabela": "tabela", "quadro": "tabela", "figura": "figura", "grafico": "gráfico", "gráfico": "gráfico"}


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


def _caption_issues(p, exact):
    issues = []
    if p.align in ("center", "right", "justify") and (exact or p.align != "justify"):
        issues.append(f"alinhamento {p.align} (esperado à esquerda)")
    sizes = {r.size for r in p.visible_runs() if r.size and not r.superscript}
    if sizes and not sizes_ok(sizes, 10):
        issues.append(f"fonte {'/'.join(f'{s:g}' for s in sorted(sizes))}pt (esperado 10pt)")
    if is_simple(p, exact) is False:
        issues.append(f"espaçamento entre linhas {p.line_spacing:g} (esperado simples)")
    return issues


def _n_tables(ctx):
    return len(ctx.doc.tables) if ctx.doc.exact else sum(1 for k, _, _ in captions(ctx) if k == "tabela")


def item_54(ctx: Ctx):
    desc = "Apresenta no máximo 5 figuras e/ou tabelas, apresentadas no corpo do texto"
    nt, ni = _n_tables(ctx), len(ctx.doc.images)
    ncap = len(captions(ctx))
    total = max(nt + ni, ncap)
    msg = f"{nt} tabela(s) e {ni} imagem(ns); {ncap} legenda(s) de tabela/figura/gráfico (total {total})"
    if not ctx.doc.exact:
        msg += " — no PDF, tabelas são contadas pelas legendas"
    return res(54, desc, "NA" if total > 5 else "A", msg)


def _images_after_table_captions(ctx):
    paras = ctx.doc.paragraphs
    hits = []
    for kind, n, p in captions(ctx):
        if kind != "tabela":
            continue
        for q in paras[p.index + 1:p.index + 4]:
            if q.n_images:
                hits.append(n)
                break
            if q.stripped:
                break
    return hits


def item_58(ctx: Ctx):
    desc = "Tabelas são elaboradas no Word (editáveis, não como imagem)"
    doc = ctx.doc
    img_tabs = _images_after_table_captions(ctx)
    as_fig = [n for k, n, p in captions(ctx) if k == "figura" and re.match(r"^\s*Figura\s*\d+\s*[.\-–:]?\s*(Tabela|Quadro)\b", p.stripped, re.IGNORECASE)]
    if as_fig:
        return res(58, desc, "NA", f"Figura(s) {', '.join(map(str, as_fig))} parecem ser tabelas inseridas como imagem — refaça no Word como tabela editável")
    ncap = sum(1 for k, _, _ in captions(ctx) if k == "tabela")
    if img_tabs:
        return res(58, desc, "NA", f"Tabela(s) {', '.join(map(str, img_tabs))} inserida(s) como imagem — refaça no Word")
    if not doc.exact:
        return res(58, desc, "-" , f"{ncap} legenda(s) de tabela; não é possível confirmar a edição em PDF (envie o .docx)")
    if doc.tables:
        extra = f"; {ncap - len(doc.tables)} legenda(s) sem tabela correspondente" if ncap > len(doc.tables) else ""
        return res(58, desc, "A", f"{len(doc.tables)} tabela(s) editável(is){extra}")
    if ncap:
        return res(58, desc, "AP", f"{ncap} legenda(s) de tabela, mas nenhuma tabela editável encontrada")
    return res(58, desc, "NSA", "O manuscrito não contém tabelas")


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


def item_61(ctx: Ctx):
    desc = "Figuras tituladas embaixo, alinhadas à esquerda, tamanho 10 e com espaçamento simples"
    exact = ctx.doc.exact
    probs, n = [], 0
    for k, (im, below, above) in enumerate(_image_captions(ctx), 1):
        cap = below or above
        if cap and cap[0] == "gráfico":
            continue
        n += 1
        if below:
            iss = _caption_issues(below[2], exact)
            if iss:
                probs.append(f"Figura {below[1]}: " + ", ".join(iss))
        elif above:
            probs.append(f"Figura {above[1]}: legenda acima da imagem (deve estar abaixo)")
        else:
            probs.append(f"Imagem {k}: legenda não encontrada")
    if n == 0:
        return res(61, desc, "NSA", "Nenhuma figura encontrada")
    return res(61, desc, "NA" if probs else "A", "; ".join(probs) if probs else f"{n} figura(s) com legenda abaixo, à esquerda, fonte 10 e espaçamento simples")


def item_121(ctx: Ctx):
    desc = "Tabelas e figuras numeradas em ordem sequencial"
    caps = captions(ctx)
    if not caps:
        return res(121, desc, "NSA", "Nenhuma legenda de tabela/figura/gráfico encontrada")
    probs = []
    for kind in ("tabela", "figura", "gráfico"):
        nums = [n for k, n, _ in caps if k == kind]
        if nums and nums != list(range(1, len(nums) + 1)):
            probs.append(f"{kind}s numeradas {nums} (esperado {list(range(1, len(nums) + 1))})")
    return res(121, desc, "NA" if probs else "A", "; ".join(probs) if probs else f"{len(caps)} legenda(s) em sequência")


def _expand(s):
    nums = set()
    for part in re.split(r"\s*(?:,|e)\s*", s):
        m = re.match(r"(\d+)\s*(?:a|-|–)\s*(\d+)$", part.strip())
        if m:
            nums.update(range(int(m.group(1)), int(m.group(2)) + 1))
        elif part.strip().isdigit():
            nums.add(int(part))
    return nums


def item_122(ctx: Ctx):
    desc = "Apresenta tabelas e ilustrações em sequência lógica, com texto complementar a essas (citadas no texto)"
    caps = captions(ctx)
    if not caps:
        return res(122, desc, "NSA", "Nenhuma legenda encontrada")
    cap_ids = {id(p) for _, _, p in caps}
    text = "\n".join(p.text for k in BODY_KEYS for p in ctx.sections.get(k) if id(p) not in cap_ids)
    cited = {"tabela": set(), "figura": set(), "gráfico": set()}
    for m in re.finditer(r"\b(Tabelas?|Quadros?|Figuras?|Gr[aá]ficos?)\s+(\d+(?:\s*(?:,|e|a|-|–)\s*\d+)*)", text, re.IGNORECASE):
        cited[KIND[m.group(1).lower().rstrip("s")]].update(_expand(m.group(2)))
    missing = [f"{k} {n}" for k, n, _ in caps if n not in cited[k]]
    return res(122, desc, "NA" if missing else "A", ("Não citadas no texto: " + ", ".join(missing)) if missing else "Todas as tabelas/figuras são citadas no texto")


def item_127(ctx: Ctx):
    desc = "Tabelas tituladas em cima, alinhadas à esquerda, fonte tamanho 10 e com espaçamento simples"
    doc, exact = ctx.doc, ctx.doc.exact
    probs, n = [], 0
    if exact and doc.tables:
        for t in doc.tables:
            n += 1
            i = t.first_para - 1
            while i >= 0 and not doc.paragraphs[i].stripped:
                i -= 1
            prev = doc.paragraphs[i] if i >= 0 else None
            if prev is not None and not prev.in_table and (m := CAP.match(prev.stripped)) and KIND[m.group(1).lower()] == "tabela":
                iss = _caption_issues(prev, exact)
                if iss:
                    probs.append(f"Tabela {m.group(2)}: " + ", ".join(iss))
                continue
            j = t.last_para + 1
            while j < len(doc.paragraphs) and not doc.paragraphs[j].stripped:
                j += 1
            nxt = doc.paragraphs[j] if j < len(doc.paragraphs) else None
            if nxt is not None and CAP.match(nxt.stripped) and KIND[CAP.match(nxt.stripped).group(1).lower()] == "tabela":
                probs.append(f"Tabela {t.index + 1}: legenda abaixo da tabela (deve estar acima)")
            else:
                probs.append(f"Tabela {t.index + 1}: legenda não encontrada")
    else:
        for k, num, p in captions(ctx):
            if k == "tabela":
                n += 1
                iss = _caption_issues(p, exact)
                if iss:
                    probs.append(f"Tabela {num}: " + ", ".join(iss))
    if n == 0:
        return res(127, desc, "NSA", "O manuscrito não contém tabelas")
    note = "" if exact else " (PDF: posição acima/abaixo da tabela não verificada)"
    return res(127, desc, "NA" if probs else "A", ("; ".join(probs) if probs else f"{n} tabela(s) com legenda correta") + note)


def item_128(ctx: Ctx):
    desc = "Nas tabelas não há linhas entre as variáveis nem linhas de fundo (apenas linhas de topo, cabeçalho e rodapé)"
    if not ctx.doc.exact:
        return res(128, desc, "-", "Verificação disponível apenas para .docx (bordas não são confiáveis em PDF)")
    if not ctx.doc.tables:
        return res(128, desc, "NSA", "O manuscrito não contém tabelas")
    probs = []
    for t in ctx.doc.tables:
        b, why = t.borders or {}, []
        if b.get("insideV") or b.get("left") or b.get("right") or b.get("cell_vertical"):
            why.append("linhas verticais")
        if b.get("insideH") or b.get("cell_inner_h"):
            why.append("linhas entre as variáveis")
        if t.shaded:
            why.append("sombreamento de fundo")
        if why:
            probs.append(f"Tabela {t.index + 1}: " + ", ".join(why))
    return res(128, desc, "NA" if probs else "A", "; ".join(probs) if probs else "Tabelas sem linhas internas/laterais")


def item_129(ctx: Ctx):
    desc = "Tabelas com espaçamento simples"
    if not ctx.doc.exact:
        return res(129, desc, "-", "Verificação disponível apenas para .docx")
    if not ctx.doc.tables:
        return res(129, desc, "NSA", "O manuscrito não contém tabelas")
    probs = []
    for t in ctx.doc.tables:
        cells = [p for p in ctx.doc.paragraphs[t.first_para:t.last_para + 1] if p.stripped]
        bad = [p for p in cells if is_simple(p, True) is False or (p.space_after or 0) > 0.5]
        if bad:
            probs.append(f"Tabela {t.index + 1}: {len(bad)} parágrafo(s) com espaçamento {bad[0].line_spacing:g}/após {bad[0].space_after:g}pt")
    return res(129, desc, "NA" if probs else "A", "; ".join(probs) if probs else "Espaçamento simples em todas as tabelas")


def item_130(ctx: Ctx):
    desc = "Figuras apresentam boa qualidade (resolução)"
    ims = [i for i in ctx.doc.images if i.kind == "picture"]
    if not ims:
        return res(130, desc, "NSA", "Nenhuma imagem encontrada")
    known = [i for i in ims if i.dpi]
    if not known:
        return res(130, desc, "-", "Resolução das imagens não pôde ser determinada")
    low = [i for i in known if i.dpi < 96]
    mid = [i for i in known if 96 <= i.dpi < 150]
    dpis = ", ".join(f"{i.dpi:.0f}" for i in known)
    if low:
        return res(130, desc, "NA", f"{len(low)} imagem(ns) com resolução baixa (<96 dpi efetivos). DPI efetivos: {dpis}")
    if mid:
        return res(130, desc, "AP", f"{len(mid)} imagem(ns) entre 96 e 150 dpi. DPI efetivos: {dpis}")
    return res(130, desc, "A", f"DPI efetivos: {dpis}. Nitidez/legibilidade devem ser conferidas visualmente.")


def item_131(ctx: Ctx):
    desc = "Títulos de tabelas/figuras com conteúdo explicativo e informação sobre o recorte geográfico e temporal"
    caps = captions(ctx)
    if not caps:
        return res(131, desc, "NSA", "Nenhuma legenda encontrada")
    probs = []
    for k, n, p in caps:
        t = p.stripped
        miss = []
        if not re.search(r"\b(19|20)\d{2}\b", t):
            miss.append("recorte temporal")
        if not (has_uf(t) or re.search(r"Brasil|Brazil|Am[ée]rica|Regi[ãa]o|Mundo|munic[ií]pio", t, re.IGNORECASE)):
            miss.append("recorte geográfico")
        if len(t.split()) < 8:
            miss.append("conteúdo explicativo (título curto)")
        if miss:
            probs.append(f"{k.capitalize()} {n}: falta " + " e ".join(miss))
    if not probs:
        return res(131, desc, "A", "Legendas com conteúdo explicativo, local e período")
    return res(131, desc, "NA" if len(probs) == len(caps) else "AP", "; ".join(probs))


def item_132(ctx: Ctx):
    desc = "Gráficos padronizados na cor preta, preferencialmente em colunas"
    has = any(k == "gráfico" for k, _, _ in captions(ctx)) or any(i.kind == "chart" for i in ctx.doc.images)
    return res(132, desc, "-" if has else "NSA", "Verificar manualmente a cor e o layout dos gráficos" if has else "O manuscrito não contém gráficos")


def item_133(ctx: Ctx):
    desc = "Gráficos titulados em cima, alinhados à esquerda, fonte tamanho 10 e espaçamento simples"
    caps = [c for c in captions(ctx) if c[0] == "gráfico"]
    if not caps:
        return res(133, desc, "NSA", "O manuscrito não contém gráficos")
    probs = []
    ims = [i.para_index for i in ctx.doc.images]
    for _, n, p in caps:
        after = any(0 < i - p.index <= 4 for i in ims)
        before = any(0 < p.index - i <= 4 for i in ims)
        iss = _caption_issues(p, ctx.doc.exact)
        if before and not after:
            iss.insert(0, "legenda abaixo do gráfico (deve estar acima)")
        if iss:
            probs.append(f"Gráfico {n}: " + ", ".join(iss))
    return res(133, desc, "NA" if probs else "A", "; ".join(probs) if probs else f"{len(caps)} gráfico(s) com legenda correta")
