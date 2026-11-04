"""SÍMBOLOS, ABREVIATURAS E SIGLAS — itens 125 e 126."""
import re

from common import Ctx, fmt_list, res
from structure import BODY_KEYS

WHITELIST = {"HIV", "AIDS", "DNA", "RNA", "COVID-19", "PCR", "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII",
             "SARS-COV-2", "CEP", "CAAE", "OMS", "UTI"} - {"OMS", "UTI"}      # OMS/UTI exigem extenso na primeira aparição
ACR = re.compile(r"(?<![\wÀ-ÿ-])([A-ZÀ-Ú]{2,8}(?:-\d+)?)(?![\wÀ-ÿ])")


def item_125(ctx: Ctx):
    desc = "Acrônimos desconhecidos escritos por extenso na primeira aparição, com a sigla entre parênteses"
    S = ctx.sections
    text = "\n".join(p.text for k in BODY_KEYS for p in S.get(k))
    if not text.strip():
        return res(125, desc, "-", "Corpo do texto não encontrado")
    seen, missing = set(), []
    for m in ACR.finditer(text):
        a = m.group(1)
        if a in seen or a.upper() in WHITELIST:
            continue
        seen.add(a)
        before = text[max(0, m.start() - 3):m.start()]
        after = text[m.end():m.end() + 40]
        defined_paren = bool(re.search(r"\(\s*$", text[:m.start()][-3:])) and re.match(r"\s*\)", text[m.end():m.end() + 3])
        defined_after = bool(re.match(r"\s*\(\s*[a-zà-ú]", after))
        if not (defined_paren or defined_after):
            missing.append(a)
    if not seen:
        return res(125, desc, "A", "Nenhuma sigla encontrada no corpo do texto")
    if not missing:
        return res(125, desc, "A", f"{len(seen)} sigla(s), todas definidas na primeira aparição")
    ratio = len(missing) / len(seen)
    return res(125, desc, "AP" if ratio <= 0.5 else "NA",
               f"Siglas sem extenso na primeira aparição ({len(missing)}/{len(seen)}): {fmt_list(missing, 10, ', ')}")


def item_126(ctx: Ctx):
    desc = "Termos COVID-19, HIV e AIDS escritos dessa maneira (caso a temática esteja relacionada)"
    S = ctx.sections
    text = "\n".join(p.text for k in ("RESUMO", "ABSTRACT", "RESUMEN") + BODY_KEYS for p in S.get(k))
    if not re.search(r"covid|hiv|aids|sars", text, re.IGNORECASE):
        return res(126, desc, "NSA", "Temática não relacionada a COVID-19/HIV/AIDS")
    bad = set()
    for m in re.finditer(r"\b(?:covid(?:-?\s?19)?|Covid(?:-?\s?19)?|COVID(?!-19)(?:\s?19|19)?|hiv|Hiv|aids|Aids)\b", text):
        w = m.group(0)
        if w not in ("COVID-19", "HIV", "AIDS"):
            bad.add(w)
    if bad:
        return res(126, desc, "NA", f"Grafia incorreta: {fmt_list(sorted(bad), 6, ', ')} (use COVID-19, HIV, AIDS)")
    return res(126, desc, "A", "Grafia correta de COVID-19/HIV/AIDS")
