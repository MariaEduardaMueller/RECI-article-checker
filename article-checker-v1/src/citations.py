"""REFERÊNCIAS AO LONGO DO TEXTO — itens 134, 135 e 136."""
import re

from common import Ctx, fmt_list, res
from structure import BODY_KEYS

CITE_RX = re.compile(r"^\s*\d+(?:\s*[,\-–]\s*\d+)*\s*$")


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
    return [p for k in keys for p in ctx.sections.get(k) if not re.match(r"^\s*(Tabela|Quadro|Figura|Gr[aá]fico)\s*\d+", p.stripped, re.I)]


def cited_numbers(ctx: Ctx, keys=BODY_KEYS) -> list[int]:
    nums = []
    for p in body_paragraphs(ctx, keys):
        for g in superscript_groups(p):
            nums += expand(g[0])
    return nums


def item_134(ctx: Ctx):
    desc = "Citações no texto sobrescritas, sem parênteses, sempre no final do parágrafo, após o ponto final"
    total, bad, paren = 0, [], []
    for p in body_paragraphs(ctx):
        t = p.text
        for g in superscript_groups(p):
            total += 1
            before = t[:g[1]].rstrip()
            after = t[g[2]:].strip()
            if not before.endswith((".", "!", "?")):
                bad.append("citação antes do ponto final / no meio da frase")
        paren += re.findall(r"\(\s*\d{1,3}(?:\s*[,\-–]\s*\d{1,3})*\s*\)|\[\s*\d{1,3}(?:\s*[,\-–]\s*\d{1,3})*\s*\]", t)
    msgs = []
    if paren:
        msgs.append(f"citações entre parênteses/colchetes: {fmt_list(paren, 4, ', ')}")
    if total == 0 and not paren:
        return res(134, desc, "NA", "Nenhuma citação numérica sobrescrita encontrada no texto")
    if bad:
        from collections import Counter
        msgs += [f"{v}× {k}" for k, v in Counter(bad).items()]
    if msgs:
        return res(134, desc, "AP" if total and len(bad) + len(paren) <= 0.2 * total else "NA", "; ".join(msgs))
    return res(134, desc, "A", f"{total} citação(ões) sobrescrita(s) ao final dos parágrafos, após o ponto")


def item_135(ctx: Ctx):
    desc = ("Referências em ordem sequencial numérica, todas citadas, separadas por vírgula e, em sequências, por hífen "
            "(ex.: 7,10-16)")
    from references import reference_entries
    order, hyphen_issues = [], []
    for p in body_paragraphs(ctx):
        for g in superscript_groups(p):
            nums = expand(g[0])
            order += nums
            # 3 ou mais números consecutivos separados por vírgula deveriam usar hífen
            plain = [int(x) for x in re.split(r"\s*,\s*", g[0]) if x.strip().isdigit()]
            run = 1
            for a, b in zip(plain, plain[1:]):
                run = run + 1 if b == a + 1 else 1
                if run >= 3:
                    hyphen_issues.append(g[0])
                    break
    if not order:
        return res(135, desc, "NA", "Nenhuma citação numérica sobrescrita encontrada")
    msgs, seen_max, out_of_order = [], 0, []
    for n in order:
        if n > seen_max + 1:
            out_of_order.append(n)
        seen_max = max(seen_max, n)
    if out_of_order:
        msgs.append(f"ordem de citação não sequencial (primeira aparição fora de ordem: {fmt_list(sorted(set(out_of_order)), 6, ', ')})")
    n_refs = len(reference_entries(ctx))
    if n_refs:
        uncited = sorted(set(range(1, n_refs + 1)) - set(order))
        beyond = sorted({n for n in order if n > n_refs})
        if uncited:
            msgs.append(f"referências não citadas no texto: {fmt_list(uncited, 8, ', ')}")
        if beyond:
            msgs.append(f"citações sem referência correspondente: {fmt_list(beyond, 8, ', ')}")
    status = "NA" if msgs else "A"
    if hyphen_issues:
        msgs.append(f"use hífen em sequências (ex.: 1-3 em vez de {hyphen_issues[0]})")
        status = "AP" if status == "A" else status
    return res(135, desc, status, "; ".join(msgs) if msgs else f"{len(set(order))} referência(s) citadas em ordem sequencial")


def item_136(ctx: Ctx):
    desc = "Evita citações com os nomes de autores em destaque no texto"
    pats = [
        r"\b(?:segundo|de acordo com|conforme)\s+(?:[a-zà-ú]{1,3}\s+)?(?!Tabela|Figura|Quadro|Gr[aá]fico|Resolu|Portaria|Lei\b|Decreto|OMS|Organiza|Minist|Conselho|Instituto|CID|Sociedade|Associa|Consenso|Diretriz|Protocolo|Sistema|Hospital|Universidade|Manual|Surviving|Sepse|Estudo|Pesquisa|Autor|Funda)[A-ZÀ-Ú][\wÀ-ÿ]+(?:\s+et\s+al\.?)?",
        r"[A-ZÀ-Ú][\wÀ-ÿ]+(?:\s+et\s+al\.?|\s+e\s+[A-ZÀ-Ú][\wÀ-ÿ]+)?\s*\(\s*(?:19|20)\d{2}\s*\)",
        r"\(\s*[A-ZÀ-Ú][\wÀ-ÿ]+(?:\s+et\s+al\.?)?,?\s+(?:19|20)\d{2}\s*\)",
        r"\b[A-ZÀ-Ú][\wÀ-ÿ]+\s+et\s+al\.?",
    ]
    hits = []
    for p in body_paragraphs(ctx):
        for rx in pats:
            hits += [m.group(0).strip() for m in re.finditer(rx, p.text)]
    hits = list(dict.fromkeys(hits))
    if hits:
        return res(136, desc, "NA", "Nomes de autores em destaque no texto: " + fmt_list(hits, 4, ", "))
    return res(136, desc, "A", "Nenhuma citação com nome de autor em destaque")
