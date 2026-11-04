"""FOLHA DE ROSTO — título, autores, ORCID/Lattes, afiliação, biografia, e-mail, rede social e contribuições."""
import re

from common import Ctx, fmt_list, has_uf, res
from document_model import Document

AUTHORS_PATTERN = r"^Autor\s*:\s*(.*)"
NO_COVER = "Folha de rosto não fornecida."

PROFESSIONAL_CATEGORIES = [
    r"\bMestrand[oa]\b", r"\bMestre\b", r"\bMestra\b", r"\bDoutorand[oa]\b", r"\bDoutor[a]?\b", r"\bGraduand[oa]\b",
    r"\bGraduad[oa]\b", r"\bEspecialista\b", r"\bProfessor[a]?\b", r"\bPós-Doutorand[oa]\b", r"\bPós-Doutor[a]?\b",
    r"\bEnfermeir[oa]\b", r"\bFarmacêutic[oa]\b", r"\bMédic[oa]\b", r"\bTécnic[oa]\b", r"\bPesquisador[a]?\b",
    r"\bNutricionista\b", r"\bFisioterapeuta\b", r"\bPsicólog[oa]\b", r"\bDentista\b", r"\bResidente\b",
]
TITULATIONS = [
    r"\bMestrado\b", r"\bDoutorado\b", r"\bGraduação\b", r"\bEspecialização\b", r"\bEspecialista\b",
    r"\bPós-Graduação\b", r"\bPós-Doutorado\b", r"\bBacharelado\b", r"\bLicenciatura\b", r"\bGraduando\b",
    r"\bGraduado\b", r"\bResidência\b", r"\bMBA\b",
]


def _authors(text):
    return [a.strip() for a in re.findall(AUTHORS_PATTERN, text, re.MULTILINE)]


def _guard(ctx: Ctx, item, desc):
    return None if ctx.cover else res(item, desc, "-", NO_COVER)


# ----- subverificações do item 10 ---------------------------------------------------
def _check_names(text):
    bad = []
    for a in _authors(text):
        w = a.split()
        if "." in a or len(w) < 2 or any(len(x) == 1 for x in w):
            bad.append(a)
    return ("NA", f"nomes incompletos/abreviados: {'; '.join(bad)}") if bad else ("A", "")


def _check_orcid_lattes(text):
    n = len(_authors(text))
    orcids = re.findall(r"ORCID:\s*https?://orcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[\dX]", text)
    lattes = re.findall(r"Curr[ií]culo\s+lattes:\s*https?://lattes\.cnpq\.br/\d+", text, re.IGNORECASE)
    if n and n == len(orcids) == len(lattes):
        return "A", ""
    return "NA", f"{n} autores, {len(orcids)} ORCID(s), {len(lattes)} Lattes"


def _check_affiliation(text):
    affs = re.findall(r"Afilia[çc][ãa]o:\s*(.*?)\.\s*(?:\n|$)", text)
    if not affs:
        return "NA", "nenhuma afiliação encontrada"
    bad = [a for a in affs if not has_uf(a)]
    return ("NA", f"afiliação sem cidade/UF: {fmt_list(bad, 3)}") if bad else ("A", "")


def _check_bio(text):
    pat = r"Resumo da Biografia:\s*((?:(?!Autor(?:\s+Correspondente)?:|Contribuições dos autores:).)+)"
    bios = [b.strip() for b in re.findall(pat, text, re.MULTILINE | re.DOTALL)]
    n = len(_authors(text))
    msgs = []
    if len(bios) != n:
        msgs.append(f"{len(bios)} biografias para {n} autores")
    for i, b in enumerate(bios, 1):
        if not any(re.search(p, b, re.IGNORECASE) for p in PROFESSIONAL_CATEGORIES):
            msgs.append(f"biografia {i}: falta categoria profissional")
        if not any(re.search(p, b, re.IGNORECASE) for p in TITULATIONS):
            msgs.append(f"biografia {i}: falta maior titulação")
    return ("NA", "; ".join(msgs)) if msgs else ("A", "")


def _check_title(doc: Document):
    m = re.search(r"^\s*(?:T[ií]tulo|Title)\s*:\s*(\S.+)$", doc.text, re.MULTILINE | re.IGNORECASE)
    if m:
        return "A", ""
    for p in doc.paragraphs:
        t = p.stripped
        if re.match(r"^Autor\s*:", t):
            break
        if len(t.split()) >= 4:
            return "A", ""
    return "NA", "título do artigo não encontrado na folha de rosto"


def item_5(ctx: Ctx):
    desc = "Resumo da Biografia (categoria profissional e maior titulação)"
    if g := _guard(ctx, 5, desc):
        return g
    st, msg = _check_bio(ctx.cover.text)
    return res(5, desc, st, msg or "Biografias com categoria profissional e maior titulação")


def item_10(ctx: Ctx):
    desc = "Apresenta título, nome completo dos autores, afiliação, ORCID, lattes e biografia (folha de rosto)"
    if g := _guard(ctx, 10, desc):
        return g
    text = ctx.cover.text
    checks = {
        "título": _check_title(ctx.cover),
        "autoria": ("A", "") if _authors(text) else ("NA", "nenhum 'Autor:' encontrado"),
        "nomes": _check_names(text),
        "ORCID/Lattes": _check_orcid_lattes(text),
        "afiliação": _check_affiliation(text),
        "biografia": _check_bio(text),
    }
    bad = {k: v[1] for k, v in checks.items() if v[0] != "A"}
    if not bad:
        return res(10, desc, "A", f"{len(_authors(text))} autor(es) com todos os campos da folha de rosto")
    st = "AP" if len(bad) < len(checks) // 2 else "NA"
    return res(10, desc, st, "; ".join(f"{k}: {v}" for k, v in bad.items()))


def item_107(ctx: Ctx):
    desc = "E-mail do autor correspondente"
    if g := _guard(ctx, 107, desc):
        return g
    text = ctx.cover.text
    email = r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+"
    m = re.search(r"Autor\s+Correspondente.*", text, re.IGNORECASE | re.DOTALL)
    if m and re.search(email, m.group(0)):
        return res(107, desc, "A", "E-mail do autor correspondente encontrado")
    if re.search(email, text):
        return res(107, desc, "AP", "E-mail encontrado, mas sem a identificação 'Autor Correspondente'")
    return res(107, desc, "NA", "E-mail do autor correspondente não encontrado")


def item_108(ctx: Ctx):
    desc = "Rede social de todos os autores (preferencialmente Instagram) para divulgação do artigo"
    if g := _guard(ctx, 108, desc):
        return g
    text = ctx.cover.text
    n = len(_authors(text))
    handles = set(re.findall(r"(?<![\w.])@[A-Za-z0-9_.]{3,}", text)) | \
        set(re.findall(r"(?:instagram|twitter|x|linkedin|facebook)\.com/[\w.\-/]+", text, re.IGNORECASE))
    k = len(handles)
    if n and k >= n:
        return res(108, desc, "A", f"{k} perfil(is) de rede social para {n} autor(es)")
    if k:
        return res(108, desc, "AP", f"{k} perfil(is) de rede social para {n} autor(es)")
    return res(108, desc, "NA", "Nenhuma rede social encontrada na folha de rosto")


# ----- item 11: contribuições individuais ------------------------------------------
def item_11(ctx: Ctx):
    desc = ("São especificadas quais foram as contribuições individuais de cada autor na elaboração do artigo: "
            "nome completo de cada autor (em negrito e por extenso), seguido das contribuições.")
    if g := _guard(ctx, 11, desc):
        return g
    paras = ctx.cover.paragraphs
    start = next((i for i, p in enumerate(paras)
                  if re.search(r"Contribuições\s+dos\s+autores\s*:", p.text, re.IGNORECASE)), None)
    if start is None:
        return res(11, desc, "NA", "Seção 'Contribuições dos autores:' não encontrada")

    authors = [re.sub(r"\d+$", "", a).strip() for a in _authors("\n".join(p.stripped for p in paras[:start]))]

    entries = []
    for p in paras[start + 1:]:
        t = p.stripped
        if not t:
            continue
        if t.startswith(("Autor Correspondente", "Endereço", "Todos os autores")):
            break
        bold, rest, in_bold = "", "", True
        for r in p.runs:
            if in_bold and r.bold:
                bold += r.text
            else:
                in_bold = False
                rest += r.text
        entries.append((bold.strip(), rest.strip()))

    if not entries:
        return res(11, desc, "NA", "Nenhuma contribuição de autor encontrada")
    found = []
    for bold, rest in entries:
        if not bold:
            return res(11, desc, "NA", "Contribuição sem nome do autor em negrito")
        names = [n.strip() for n in re.split(r"\s+e\s+|,", bold) if n.strip()]
        if any(len(n.split()) < 2 or "." in n for n in names):
            return res(11, desc, "NA", f"Nome incompleto ou abreviado: '{bold}'")
        if not rest:
            return res(11, desc, "NA", f"Autor '{bold}' sem descrição de contribuição")
        found += names
    norm = lambda s: s.lower().strip()
    missing = [a for a in authors if not any(norm(a) in norm(f) or norm(f) in norm(a) for f in found)]
    if missing:
        return res(11, desc, "NA", f"Autores sem contribuição descrita: {', '.join(missing)}")
    return res(11, desc, "A", f"Contribuições de {len(found)} autor(es) com nome em negrito e por extenso")


def item_109(ctx: Ctx):
    desc = "Apresenta o título do artigo (folha de rosto)"
    if g := _guard(ctx, 109, desc):
        return g
    st, msg = _check_title(ctx.cover)
    return res(109, desc, st, msg or "Título encontrado na folha de rosto")
