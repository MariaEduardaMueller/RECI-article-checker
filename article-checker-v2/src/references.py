"""REFERÊNCIAS — Normas de Vancouver adaptadas pela RECI (somente o link, sem "Disponível em:"),
formatação, DOI/URL em hiperlink, autores, "et al", atualidade e origem."""
import datetime
import re
from dataclasses import dataclass

from common import Ctx, fmt_list, is_simple, note, recent_cutoff, res, sizes_ok
from document_model import Para
from lang import detect_language

URL_RX = re.compile(r"https?://[^\s;,)]+|doi\.org/\S+|\bdoi:\s*\S+|\b10\.\d{4,9}/\S+", re.IGNORECASE)
AVAILABLE_RX = re.compile(r"\b(?:dispon[ií]vel\s+(?:em|no|na|at)|available\s+(?:from|at|in|on)|acesso\s+em|acessado\s+em|accessed|\[?\s*cited\b)\s*:?", re.IGNORECASE)


@dataclass
class Ref:
    num: int
    text: str
    para: Para


def reference_entries(ctx: Ctx) -> list[Ref]:
    def build():
        entries: list[Ref] = []
        for p in ctx.sections.get("REFERENCES"):
            t = p.stripped
            m = re.match(r"^(\d{1,3})\s*[.,)\-–]\s*(\S.*)$", t, re.S)
            if m:
                entries.append(Ref(int(m.group(1)), m.group(2).strip(), p))
            elif p.numbered or not entries or re.search(r"[.)/]\s*$", entries[-1].text) and t[:1].isupper():
                entries.append(Ref(len(entries) + 1, t, p))
            else:
                entries[-1].text += " " + t
        return _split_merged(entries)
    return ctx.memo("refs", build)


def _split_merged(entries):
    """Separa referências coladas por perda de quebra de linha (ex.: '...4343' + '11. Skypala IJ.')."""
    have = {e.num for e in entries}
    out = []
    for e in entries:
        cur = e
        while True:
            nxt = cur.num + 1
            if nxt in have:
                break
            m = re.search(rf"{nxt}\.\s+(?=[A-ZÀ-Ú][\wÀ-ÿ'’-]+(?:\s+[\wÀ-ÿ'’-]+){{0,2}}\s+[A-ZÀ-Ú]{{1,3}}[ ,.])", cur.text[20:])
            if not m:
                break
            cut = 20 + m.start()
            new = Ref(nxt, cur.text[20 + m.end():].strip(), cur.para)
            cur.text = cur.text[:cut].rstrip()
            out.append(cur)
            have.add(nxt)
            cur = new
        out.append(cur)
    return out


def _no_refs(item, desc):
    return res(item, desc, "NA", "Seção de referências não encontrada ou sem referências numeradas")


def author_part(text: str) -> str:
    m = re.search(r"et\s+al\.?", text)
    if m and m.start() < 200:
        return text[:m.end()]
    return text.split(". ")[0]


def ref_year(text: str):
    t = re.sub(r"https?://\S+|doi:\s*\S+", " ", text, flags=re.IGNORECASE)
    m = re.search(r"\b((?:19|20)\d{2})\b[^;]{0,12};", t)
    if m:
        return int(m.group(1))
    ys = [int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", t) if int(y) <= datetime.date.today().year + 1]
    return ys[-1] if ys else None


def is_international(text: str):
    rest = text[len(author_part(text)):].lstrip(". ")
    title = rest.split(". ")[0] if rest else text
    lang = detect_language(title)
    return None if lang is None else lang != "portuguese"


def _loc(ctx, r):  # "Referência 5"
    return f"Ref {r.num} ({ctx.where(r.para)})"


# ----------------------------- Vancouver --------------------------------------------------
def _vancouver_issues(ref: str):
    issues = []
    if not re.search(r"[A-ZÀ-Ú][a-zà-ú]+\s+[A-ZÀ-Ú]{1,3}\b", ref) and not re.match(r"^[A-ZÀ-Ú][\wÀ-ÿ ]+\.", ref):
        issues.append("formato de autores inválido")
    if not re.search(r"\.\s+[A-ZÀ-Ú].+?\.", ref):
        issues.append("título não identificado")
    if not re.search(r"\b(19|20)\d{2}\b", ref):
        issues.append("ano não identificado")
    if not ref.strip().endswith((".", "/")) and not re.search(r"https?://\S+$", ref):
        issues.append("falta ponto final")
    if re.search(r"et\s+al", ref, re.I) and not re.search(r"et al\.", ref):
        issues.append("'et al.' sem ponto")
    return issues


def item_rf_vancouver(ctx: Ctx):
    desc = "Apresentam-se nas Normas de Vancouver (somente o link, sem “Disponível em:”/“Available from:”)"
    refs = reference_entries(ctx)
    if not refs:
        return _no_refs("rf.vancouver", desc)
    notes, msgs = [], []
    bad = [(r, i) for r in refs if len(i := _vancouver_issues(r.text)) > 1]
    for r, i in bad:
        notes.append(note(r.para, f"Referência fora do padrão Vancouver: {', '.join(i)}."))
    avail = []
    for r in refs:
        for m in AVAILABLE_RX.finditer(r.para.text):
            avail.append(r)
            notes.append(note(r.para, f"Remova “{m.group(0).strip()}”: a RECI pede apenas o link (DOI ou endereço eletrônico) ao final da referência.", m.start(), m.end()))
            break
    seq = [r.num for r in refs]
    if seq != list(range(1, len(refs) + 1)):
        msgs.append(f"numeração fora de sequência ({fmt_list(seq, 8, ',')})")
    if bad:
        msgs.append(f"{len(refs) - len(bad)}/{len(refs)} em formato adequado. " + fmt_list([f"{_loc(ctx, r)}: {', '.join(i)}" for r, i in bad], 3))
    if avail:
        msgs.append("“Disponível em:/Available from:” presente em " + fmt_list([_loc(ctx, r) for r in avail], 4) + " — manter só o link")
    if msgs:
        return res("rf.vancouver", desc, "NA", "; ".join(msgs), notes)
    return res("rf.vancouver", desc, "A", f"{len(refs)}/{len(refs)} referências em formato Vancouver. Abreviação dos periódicos (Index Medicus/MedLine) deve ser conferida manualmente.")


# ----------------------------- fonte/espaçamento/alinhamento ---------------------------------
def item_rf_formato(ctx: Ctx):
    desc = "Referências em fonte 12, espaçamento simples, justificado"
    refs = reference_entries(ctx)
    if not refs:
        return _no_refs("rf.formato", desc)
    issues, notes = [], []
    for r in refs:
        p, why = r.para, []
        sizes = {x.size for x in p.visible_runs() if x.size and not x.superscript}
        if sizes and not sizes_ok(sizes, 12):
            why.append(f"fonte {'/'.join(f'{s:g}' for s in sorted(sizes))}pt")
        if is_simple(p) is False or (p.space_after or 0) > 0.5:
            why.append("espaçamento incorreto")
        if p.align not in ("justify", None):
            why.append({"left": "alinhada à esquerda", "center": "centralizada", "right": "alinhada à direita"}.get(p.align, p.align))
        if why:
            issues.append(f"Ref {r.num}: {', '.join(why)}")
            notes.append(note(p, f"Referência deve estar em fonte 12, espaçamento simples e justificada ({', '.join(why)})."))
    if not issues:
        return res("rf.formato", desc, "A", f"{len(refs)} referências formatadas corretamente")
    return res("rf.formato", desc, "NA", f"{len(refs)} referências; {len(issues)} com problema: " + fmt_list(issues, 3), notes[:6])


# ----------------------------- DOI/URL em hiperlink ---------------------------------------------
def item_rf_doi(ctx: Ctx):
    desc = "Apresentam DOI nas referências ou endereço eletrônico (em hiperlink)"
    refs = reference_entries(ctx)
    if not refs:
        return _no_refs("rf.doi", desc)
    missing = [r for r in refs if not URL_RX.search(r.text)]
    nolink, notes = [], []
    for r in missing:
        notes.append(note(r.para, "Inclua o DOI ou o endereço eletrônico ao final desta referência."))
    for r in refs:
        if r in missing:
            continue
        p = r.para
        for m in URL_RX.finditer(p.text):
            runs = p.runs_in(m.start(), m.end())
            if runs and not all(x.link for x in runs):
                nolink.append(r)
                notes.append(note(p, "O DOI/endereço eletrônico deve estar em hiperlink (Inserir > Link).", m.start(), m.end()))
                break
    msgs = []
    if missing:
        msgs.append(f"{len(refs) - len(missing)}/{len(refs)} com DOI/URL; faltam nas refs: {fmt_list([r.num for r in missing], 8, ', ')}")
    if nolink:
        msgs.append(f"link sem hiperlink nas refs: {fmt_list([r.num for r in nolink], 8, ', ')}")
    if msgs:
        status = "NA" if missing else "AP"
        return res("rf.doi", desc, status, "; ".join(msgs), notes[:8])
    return res("rf.doi", desc, "A", f"Todas as {len(refs)} referências possuem DOI/URL em hiperlink")


# ----------------------------- autores ---------------------------------------------------------
def item_rf_autores(ctx: Ctx):
    desc = "Autores pelo sobrenome; letra inicial maiúscula, seguida do(s) nome(s) abreviado(s) e sem ponto (ex.: Posma DM, Bill D)"
    refs = reference_entries(ctx)
    if not refs:
        return _no_refs("rf.autores", desc)
    particles = r"(?:de|da|do|dos|das|del|della|di|van|von|der|den|het|ter|te|ten|el|la|las|los|le|e)"
    issues, notes = [], []
    for r in refs:
        a = author_part(r.text)
        why = []
        if re.search(r"[A-ZÀ-Ú][a-zà-úç]+\s+[A-ZÀ-Ú]\.\s*(?:[A-ZÀ-Ú]\.|,)|[A-ZÀ-Ú]\.[A-ZÀ-Ú]\.", a):
            why.append("iniciais com pontos")
        if re.search(rf"(?:^|,\s*)(?!{particles}\b)[a-zà-úç]+\s+[A-ZÀ-Ú]{{1,3}}\b", a):
            why.append("sobrenome em minúscula")
        has_pattern = re.search(r"[A-ZÀ-ÞĀ-Ž][^\s,.]+\s+[A-ZÀ-Þ]{1,3}(?![.\w])", a)
        collective = len(a.split()) >= 2 and not re.search(r"\b[A-ZÀ-Ú]{1,3}\b(?=\s*(?:,|$))", a)
        if not why and not (has_pattern or collective):
            why.append("formato de autores não identificado")
        if why:
            issues.append(f"Ref {r.num}: {', '.join(why)}")
            notes.append(note(r.para, f"Autores devem seguir o padrão “Sobrenome INICIAIS” sem pontos, ex.: Posma DM, Bill D ({', '.join(why)})."))
    if issues:
        return res("rf.autores", desc, "NA", f"{len(refs) - len(issues)}/{len(refs)} corretas. " + fmt_list(issues, 4), notes[:6])
    return res("rf.autores", desc, "A", f"{len(refs)}/{len(refs)} referências com formatação correta de autores")


# ----------------------------- et al / designação familiar ------------------------------------------
FAMILIAR_WRONG = re.compile(r"\b[A-ZÀ-Ú]{1,3}\s+(?:J[uú]nior|Neto|Netto|Filho|Sobrinho|Segundo|Terceiro)\b")


def item_rf_etal(ctx: Ctx):
    desc = "Mais de 6 autores: citar os três primeiros nomes antes de 'et al'; designação familiar logo após o sobrenome"
    refs = reference_entries(ctx)
    if not refs:
        return _no_refs("rf.etal", desc)
    author_rx = r"[A-ZÀ-Ú][\wÀ-ÿ'’\-]+(?:\s+[A-ZÀ-Ú]{1,4}(?![\wÀ-ÿ]))"
    issues, notes, n_etal = [], [], 0
    for r in refs:
        a = author_part(r.text)
        m = re.search(r"(.*?),?\s*et\s+al\.?", a, re.IGNORECASE)
        if m:
            n_etal += 1
            k = len(re.findall(author_rx, m.group(1)))
            if k != 3:
                issues.append(f"Ref {r.num}: {k} autor(es) antes de 'et al' (esperado exatamente 3)")
                notes.append(note(r.para, f"Com mais de 6 autores, cite os três primeiros seguidos de “et al.” (encontrados {k} antes do et al)."))
        else:
            k = len([x for x in a.split(",") if x.strip()])
            if k > 6 and re.search(author_rx, a):
                issues.append(f"Ref {r.num}: {k} autores listados sem 'et al' (mais de 6: use os 3 primeiros + et al)")
                notes.append(note(r.para, f"{k} autores listados: com mais de 6 autores, cite os três primeiros seguidos de “et al.”."))
        fm = FAMILIAR_WRONG.search(a)
        if fm:
            issues.append(f"Ref {r.num}: designação familiar após as iniciais ('{fm.group(0)}')")
            notes.append(note(r.para, "A designação familiar (Júnior, Neto, Filho...) deve vir logo após o sobrenome, ex.: Morais Neto OL.", fm.start(), fm.end()))
    if issues:
        return res("rf.etal", desc, "NA", fmt_list(issues, 4), notes[:6])
    return res("rf.etal", desc, "A", f"{n_etal} referência(s) com 'et al' formatadas corretamente" if n_etal else "Nenhuma referência com 'et al' fora do padrão")


# ----------------------------- atualidade e origem ---------------------------------------------------
def _stats(refs):
    cut = recent_cutoff()
    rows = []
    for r in refs:
        y = ref_year(r.text)
        rows.append((r, y, y is not None and y >= cut, is_international(r.text)))
    return rows, cut


def item_cat_refs(ctx: Ctx):
    desc = "Artigo original: mínimo de 10 e máximo de 25 referências nos últimos 5 anos"
    refs = reference_entries(ctx)
    if not refs:
        return _no_refs("cat.refs", desc)
    rows, cut = _stats(refs)
    n = sum(1 for _, _, rec, _ in rows if rec)
    msg = f"{n} referência(s) de {cut} em diante (de {len(refs)} no total)"
    if n < 10:
        return res("cat.refs", desc, "NA", msg + " — mínimo 10")
    if n > 25:
        return res("cat.refs", desc, "NA", msg + " — máximo 25")
    return res("cat.refs", desc, "A", msg)


def item_rf_recentes(ctx: Ctx):
    desc = "Utilizaram-se referências, majoritariamente, de manuscritos publicados nos últimos cinco anos, nacionais e internacionais"
    refs = reference_entries(ctx)
    if not refs:
        return _no_refs("rf.recentes", desc)
    rows, cut = _stats(refs)
    dated = [x for x in rows if x[1]]
    rec = sum(1 for x in dated if x[2])
    share = rec / len(dated) if dated else 0
    intl = [x[3] for x in rows if x[3] is not None]
    mix = any(intl) and not all(intl)
    origin = "nacionais e internacionais" if mix else (("apenas " + ("internacionais" if all(intl) else "nacionais")) if intl else "origem não determinada")
    msg = f"{rec}/{len(dated)} referências ({share:.0%}) de {cut} em diante; {origin}"
    if share > 0.5 and mix:
        return res("rf.recentes", desc, "A", msg)
    if share > 0.5 or (share >= 0.4 and mix):
        return res("rf.recentes", desc, "AP", msg)
    return res("rf.recentes", desc, "NA", msg)


def item_rf_internacionais(ctx: Ctx):
    desc = "Apresenta, majoritariamente, 40% de referências internacionais nos últimos 5 anos"
    refs = reference_entries(ctx)
    if not refs:
        return _no_refs("rf.internacionais", desc)
    rows, cut = _stats(refs)
    k = sum(1 for _, _, rec, intl in rows if rec and intl)
    share = k / len(refs)
    msg = f"{k}/{len(refs)} referências internacionais de {cut} em diante ({share:.0%}); idioma inferido pelo título"
    return res("rf.internacionais", desc, "A" if share >= 0.4 else "NA", msg)
