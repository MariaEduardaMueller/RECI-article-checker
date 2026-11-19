"""SÍMBOLOS, ABREVIATURAS E SIGLAS — siglas por extenso na 1ª aparição; Covid-19, HIV e Aids."""
import re

from common import Ctx, fmt_list, note, res
from structure import BODY_KEYS

WHITELIST = {"SPSS", "IBM", "SAS", "SD", "IQR", "OR", "RR", "HR", "HIV", "AIDS", "VIH", "SIDA", "DNA", "RNA", "ADN", "ARN", "PCR", "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII", "CEP", "CAAE", "IC"}
ACR = re.compile(r"(?<![\wÀ-ÿ-])([A-ZÀ-Ú]{2,8}(?:-\d+)?)(?![\wÀ-ÿ])")
SHORT_WRONG = re.compile(r"\b(Dou|Usp|Oit|Sus|Oms|Uti|Ubs|Cep|Ibge)\b")


def item_si_siglas(ctx: Ctx):
    desc = "Siglas ou acrônimos com até três letras em maiúsculas; na primeira aparição, por extenso com a sigla entre parênteses"
    S = ctx.sections
    paras = [p for k in BODY_KEYS for p in S.get(k)]
    if not paras:
        return res("si.siglas", desc, "-", "Corpo do texto não encontrado")
    # definições em legendas/listas: "NR: nonreactive; FTA-ABS: fluorescent ..." ou "SPSS = Statistical Package..."
    listed = {a for p in paras for a in re.findall(r"(?<![\w-])([A-ZÀ-Ú][A-ZÀ-Ú0-9\-]{1,8})\s*[:=]\s*[A-Za-zÀ-ÿ]", p.text)}
    seen, missing, notes = set(), [], []
    for p in paras:
        t = p.text
        for m in ACR.finditer(t):
            a = m.group(1)
            if a in seen or a in listed or a.upper() in WHITELIST or a.upper() == "COVID-19" or a == "COVID":
                continue
            seen.add(a)
            # definida se a 1ª ocorrência está DENTRO de parênteses logo após a expansão: "(CMIA)", "(CMIA; produto)", "(95% CI)"
            open_i = t.rfind("(", 0, m.start())
            paren = open_i != -1 and ")" not in t[open_i:m.start()] and bool(re.search(r"[\wÀ-ÿ]\s*$", t[:open_i]))
            after = bool(re.match(r"\s*\(\s*[a-zà-ú]", t[m.end():m.end() + 40]))
            if not (paren or after):
                missing.append((a, p))
                notes.append(note(p, f"Sigla {a}: na primeira aparição escreva por extenso, seguida da sigla entre parênteses.", m.start(), m.end()))
    wrong = []
    for p in paras:
        for m in SHORT_WRONG.finditer(p.text):
            wrong.append(m.group(0))
            notes.append(note(p, f"Siglas com até três letras devem ser escritas em maiúsculas ({m.group(0).upper()}).", m.start(), m.end()))
    msgs = []
    if missing:
        msgs.append(f"Siglas sem extenso na primeira aparição ({len(missing)}/{len(seen)}): " + fmt_list([f"{a} ({ctx.where(p)})" for a, p in missing], 4))
    if wrong:
        msgs.append("siglas curtas fora de maiúsculas: " + fmt_list(sorted(set(wrong)), 4, ", "))
    if not msgs:
        return res("si.siglas", desc, "A", f"{len(seen)} sigla(s), todas definidas na primeira aparição" if seen else "Nenhuma sigla encontrada no corpo do texto")
    ratio = len(missing) / max(len(seen), 1)
    return res("si.siglas", desc, "AP" if ratio <= 0.5 and not wrong else "NA", "; ".join(msgs), notes[:12])


OK_TERMS = ("Covid-19", "HIV", "Aids")


def item_si_termos(ctx: Ctx):
    desc = "Quando presentes, os termos devem ser escritos: Covid-19, HIV, Aids"
    S = ctx.sections
    paras = [p for k in ("RESUMO", "ABSTRACT", "RESUMEN") + BODY_KEYS for p in S.get(k)]
    if not any(re.search(r"covid|hiv|vih|aids|sida|sars", p.text, re.IGNORECASE) for p in paras):
        return res("si.termos", desc, "NSA", "Temática não relacionada a Covid-19/HIV/Aids")
    from common import work_lang
    spanish = work_lang(ctx) == "spanish"             # em espanhol: VIH / sida são as formas corretas
    bad, notes = [], []
    rx = re.compile(r"\b(?:covid(?:-?\s?19)?|COVID(?:-?\s?19)?|hiv|Hiv|aids|AIDS)\b", re.IGNORECASE)
    for p in paras:
        for m in rx.finditer(p.text):
            w = m.group(0)
            low = w.lower().replace(" ", "-")
            good = "Covid-19" if low.startswith("covid") else ("HIV" if low == "hiv" else "Aids")
            if spanish and good != "Covid-19":
                continue
            if w != good:
                bad.append(f"{w} → {good} ({ctx.where(p)})")
                notes.append(note(p, f"Escreva “{good}” (em vez de “{w}”).", m.start(), m.end()))
    if bad:
        return res("si.termos", desc, "NA", "Grafia incorreta: " + fmt_list(bad, 5), notes[:12])
    return res("si.termos", desc, "A", "Grafia correta de Covid-19/HIV/Aids")
