"""REFERÊNCIAS AO LONGO DO TEXTO — numeração sequencial, sobrescrito, após o ponto final da frase,
hífen em sequências e ausência de citações com nomes de autores em destaque (por seção)."""
import re
from collections import Counter

from common import Ctx, fmt_list, note, res
from structure import BODY_KEYS

CITE_RX = re.compile(r"^\s*\d+(?:\s*[,\-–]\s*\d+)*\s*$")
CAPTION = re.compile(r"^\s*(Tabela|Quadro|Figura|Gr[aá]fico)\s*\d+", re.I)


def expand(s: str) -> list[int]:
    out = []
    for part in re.split(r"\s*,\s*", s.strip()):
        m = re.match(r"(\d+)\s*[-–]\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            out += list(range(a, b + 1)) if b >= a else [a, b]
        elif part.isdigit():
            out.append(int(part))
    return out


def superscript_groups(p):
    """[(texto, início, fim)] de grupos contíguos de sobrescrito formados só por números, vírgulas e hífens."""
    groups, pos, cur = [], 0, None
    for r in p.runs:
        start, end = pos, pos + len(r.text)
        pos = end
        if r.superscript and r.text.strip():
            cur = [r.text, start, end] if cur is None else [cur[0] + r.text, cur[1], end]
        elif cur is not None and not r.text.strip() and r.superscript:
            continue
        else:
            if cur:
                groups.append(tuple(cur))
            cur = None
    if cur:
        groups.append(tuple(cur))
    return [g for g in groups if CITE_RX.match(g[0])]


def body_paragraphs(ctx: Ctx, keys=BODY_KEYS):
    return [p for k in keys for p in ctx.sections.get(k) if not CAPTION.match(p.stripped)]


def cited_numbers(ctx: Ctx, keys=BODY_KEYS) -> list[int]:
    nums = []
    for p in body_paragraphs(ctx, keys):
        for g in superscript_groups(p):
            nums += expand(g[0])
    return nums


# ----------------------------- citações numéricas / de autores ----------------------------------------
_INST = (r"Tabela|Figura|Quadro|Gr[aá]fico|Resolu|Portaria|Lei\b|Decreto|OMS|Organiza|Minist|Conselho|Instituto|CID|Sociedade|"
         r"Associa|Consenso|Diretriz|Protocolo|Sistema|Hospital|Universidade|Manual|Surviving|Sepse|Estudo|Pesquisa|Autor|Funda")
AUTHOR_PATS = [
    rf"\b(?:segundo|de acordo com|conforme)\s+(?:[a-zà-ú]{{1,3}}\s+)?(?!{_INST})[A-ZÀ-Ú][\wÀ-ÿ]+(?:\s+et\s+al\.?)?",
    r"[A-ZÀ-Ú][\wÀ-ÿ]+(?:\s+et\s+al\.?|\s+e\s+[A-ZÀ-Ú][\wÀ-ÿ]+)?\s*\(\s*(?:19|20)\d{2}\s*\)",
    r"\(\s*[A-ZÀ-Ú][\wÀ-ÿ]+(?:\s+et\s+al\.?)?,?\s+(?:19|20)\d{2}\s*\)",
    r"\b[A-ZÀ-Ú][\wÀ-ÿ]+\s+et\s+al\.?",
]
PAREN_NUM = re.compile(r"\(\s*\d{1,3}(?:\s*[,\-–]\s*\d{1,3})*\s*\)|\[\s*\d{1,3}(?:\s*[,\-–]\s*\d{1,3})*\s*\]")


def author_hits(p):
    """[(início, fim, texto)] de citações com nome de autor em destaque no parágrafo."""
    hits = []
    for rx in AUTHOR_PATS:
        for m in re.finditer(rx, p.text):
            if not any(s < m.end() and m.start() < e for s, e, _ in hits):
                hits.append((m.start(), m.end(), m.group(0).strip()))
    return hits


def numeric_cite_hits(p):
    """Citações numéricas (sobrescritas ou entre parênteses/colchetes) — proibidas nos resumos."""
    out = [(g[1], g[2], g[0].strip()) for g in superscript_groups(p)]
    out += [(m.start(), m.end(), m.group(0)) for m in PAREN_NUM.finditer(p.text)]
    return out


def authors_item(ctx: Ctx, item_id: str, keys, label: str):
    desc = "Não apresenta citações com os nomes de autores em destaque no texto"
    notes, found = [], []
    for p in body_paragraphs(ctx, keys):
        for s, e, t in author_hits(p):
            found.append(f"“{t}” ({ctx.where(p)})")
            notes.append(note(p, f"Evite citar o nome do autor no texto (“{t}”): reescreva a frase e cite somente o número da referência, sobrescrito, após o ponto final.", s, e))
    if found:
        return res(item_id, desc, "NA", f"Nomes de autores em destaque em {label}: " + fmt_list(found, 4), notes)
    return res(item_id, desc, "A", f"Nenhuma citação com nome de autor em destaque em {label}")


def item_in_autores(ctx): return authors_item(ctx, "in.autores", ("INTRODUCTION",), "Introdução")
def item_me_autores(ctx): return authors_item(ctx, "me.autores", ("METHODS",), "Métodos")
def item_di_autores(ctx): return authors_item(ctx, "di.autores", ("DISCUSSION",), "Discussão")
def item_rt_autores(ctx): return authors_item(ctx, "rt.autores", BODY_KEYS, "todo o texto (Introdução a Discussão)")


# ----------------------------- ordem, sobrescrito e posição --------------------------------------------
def item_rt_citacoes(ctx: Ctx):
    desc = ("Referências em ordem sequencial numérica, todas citadas, sobrescritas, sem parênteses, após o ponto final da frase; "
            "separadas por vírgula e, em sequências, por hífen (ex.: 7,10-16)")
    from references import reference_entries
    issues: Counter = Counter()
    notes, where_ex = [], {}
    order, seen_max, total = [], 0, 0

    def flag(key, p, text, s, e):
        issues[key] += 1
        where_ex.setdefault(key, ctx.where(p))
        notes.append(note(p, text, s, e))

    for p in body_paragraphs(ctx):
        t = p.text
        for txt, s, e in superscript_groups(p):
            total += 1
            nums = expand(txt)
            order += nums
            if not t[:s].rstrip().endswith((".", "!", "?")):
                flag("citação antes do ponto final / no meio da frase (deve vir após o ponto final)", p,
                     "A citação deve ser colocada após o ponto final da frase (sobrescrita, sem parênteses).", s, e)
            plain = [int(x) for x in re.split(r"\s*,\s*", txt) if x.strip().isdigit()]
            run = 1
            for a, b in zip(plain, plain[1:]):
                run = run + 1 if b == a + 1 else 1
                if run >= 3:
                    flag("sequência de 3+ números com vírgula (use hífen)", p,
                         f"Em sequências, use hífen indicando só a primeira e a última referência (ex.: {plain[0]}-{plain[-1]}).", s, e)
                    break
            for n in nums:
                if n > seen_max + 1:
                    flag("ordem de citação não sequencial", p,
                         f"A referência {n} aparece antes da {seen_max + 1}: numere as referências na ordem em que são citadas.", s, e)
                seen_max = max(seen_max, n)
        for m in PAREN_NUM.finditer(t):
            flag("citação entre parênteses/colchetes (deve ser sobrescrita)", p,
                 f"Citação {m.group(0)} deve ser sobrescrita e sem parênteses/colchetes.", m.start(), m.end())
    if not order and not issues:
        first = ctx.sections.get("INTRODUCTION")
        return res("rt.citacoes", desc, "NA", "Nenhuma citação numérica sobrescrita encontrada no texto: cite as referências em sobrescrito, após o ponto final.",
                   [note(first[0] if first else None, "Nenhuma citação numérica sobrescrita encontrada no texto.")])
    refs = reference_entries(ctx)
    if refs:
        uncited = sorted(set(range(1, len(refs) + 1)) - set(order))
        beyond = sorted({n for n in order if n > len(refs)})
        if uncited:
            issues[f"referências não citadas no texto: {fmt_list(uncited, 8, ', ')}"] += 1
            notes += [note(r.para, f"A referência {r.num} não é citada no texto: cite-a ou remova-a.") for r in refs if r.num in uncited[:5]]
        if beyond:
            issues[f"citações sem referência correspondente: {fmt_list(beyond, 8, ', ')}"] += 1
    if not issues:
        return res("rt.citacoes", desc, "A", f"{len(set(order))} referência(s) citadas em ordem sequencial, sobrescritas, após o ponto final")
    inst = sum(issues.values())
    status = "AP" if len(issues) <= 2 and inst <= max(2, 0.2 * max(total, 1)) else "NA"
    msg = "; ".join(f"{k} ({v}×; ex.: {where_ex[k]})" if k in where_ex else k for k, v in issues.most_common(5))
    return res("rt.citacoes", desc, status, msg, notes)
