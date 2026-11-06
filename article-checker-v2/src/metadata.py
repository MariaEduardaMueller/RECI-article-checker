"""METADADOS do Checklist — itens 1 a 4 (autoria, nomes completos, ORCID/Lattes, afiliação)."""
import re

from common import UF_NAMES, UF_SIGLAS, Ctx, fmt_list, has_uf, res

MAX_AUTHORS = 10
_UP = "A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ"
_LO = "a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
AUTHOR_LINE = (rf"^([{_UP}][{_LO}]+(?:\s+(?:(?:de|da|do|dos|das|e|van|von)\s+)?[{_UP}][{_LO}]+)+)"
               r"\s?\d+\s*(?:,\s*\d+\s*)*ORCID\s+\d{4}-\d{4}-\d{4}-\d{3}[\dX]")


def front_text(ctx: Ctx) -> str:
    """Bloco inicial do manuscrito (título, autores, afiliações) até o RESUMO."""
    return "\n".join(p.stripped for p in ctx.sections.content.get("FRONT", []) if p.stripped)


def authors_from_manuscript(ctx: Ctx) -> list[str]:
    return re.findall(AUTHOR_LINE, front_text(ctx), re.MULTILINE)


def all_authors(ctx: Ctx):
    """(autores, origem): do manuscrito ou, se ele não os traz (versão anonimizada), da folha de rosto."""
    a = authors_from_manuscript(ctx)
    if a:
        return a, "manuscrito"
    if ctx.cover:
        c = [re.sub(r"\d+$", "", x).strip() for x in re.findall(r"^Autor\s*:\s*(.*)", ctx.cover.text, re.MULTILINE)]
        if c:
            return c, "folha de rosto"
    return [], None


def item_1(ctx: Ctx):
    desc = "A autoria é composta de, no máximo, 10 autores (exceção em multicêntricos)"
    authors, src = all_authors(ctx)
    if not authors:
        return res("fr.autores", desc, "-", "Não foi possível identificar os autores no manuscrito (esperado: 'Nome Sobrenome1 ORCID 0000-...').")
    if len(authors) > MAX_AUTHORS:
        return res("fr.autores", desc, "NA", f"{len(authors)} autores identificados (máximo {MAX_AUTHORS}): {', '.join(authors)}")
    return res("fr.autores", desc, "A", f"{len(authors)} autor(es) identificado(s) ({src})")


def item_2(ctx: Ctx):
    desc = "Nomes completos sem abreviações"
    authors, src = all_authors(ctx)
    if not authors:
        return res("fr.nomes", desc, "-", "Autores não identificados no manuscrito.")
    bad = []
    for a in authors:
        words = a.split()
        if "." in a or any(len(w) == 1 for w in words):
            bad.append(f"{a} (abreviação)")
        elif len(words) < 2:
            bad.append(f"{a} (nome único)")
    return res("fr.nomes", desc, "NA" if bad else "A", "; ".join(bad))


def item_3(ctx: Ctx):
    desc = "Links ORCID e Lattes"
    authors, src = all_authors(ctx)
    n = len(authors)
    if not n:
        return res("fr.links", desc, "-", "Autores não identificados no manuscrito.")
    texts = ctx.text + ("\n" + ctx.cover.text if ctx.cover else "")
    orcids = set(re.findall(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", texts))
    lattes = set(re.findall(r"lattes\.cnpq\.br/(\d+)", texts, re.IGNORECASE))
    ok_o, ok_l = len(orcids) >= n, len(lattes) >= n
    msg = f"{n} autores, {len(orcids)} ORCID(s), {len(lattes)} Lattes" + ("" if ctx.cover else " (sem folha de rosto, Lattes só no manuscrito)")
    if ok_o and ok_l:
        return res("fr.links", desc, "A", msg)
    return res("fr.links", desc, "AP" if (ok_o or ok_l) else "NA", msg)


_INSTITUTION = r"universidade|university|instituto|institute|faculdade|faculty|escola|school|hospital|centro|center|centre|funda[cç][aã]o|foundation|laborat[oó]rio|laboratory|secretaria|prefeitura|minist[eé]rio|col[eé]gio|santa casa|conselho"


def affiliations_from_front(text: str) -> list[str]:
    out = []
    for line in text.split("\n"):
        m = re.match(rf"^\s*(\d{{1,2}})\s*[.)\-]?\s*(?=[{_UP}])(.+)$", line.strip())
        if not m:
            continue
        body = m.group(2).strip()
        if re.search(r"ORCID|@|https?://", body):
            continue
        if re.search(_INSTITUTION, body, re.IGNORECASE) or body.count(",") >= 2:
            out.append(body.rstrip(". "))
    return out


def item_4(ctx: Ctx):
    desc = "Instituição/Afiliação (com cidade e UF)"
    affs = affiliations_from_front(front_text(ctx))
    if not affs and ctx.cover:
        affs = [x.strip() for x in re.findall(r"Afilia[çc][ãa]o:\s*(.*?)\.\s*(?:\n|$)", ctx.cover.text)]
    if not affs:
        authors, _ = all_authors(ctx)
        if not authors:
            return res("fr.afiliacao", desc, "-", "Manuscrito sem autores/afiliações (versão anonimizada?) e folha de rosto não fornecida.")
        return res("fr.afiliacao", desc, "NA", "Nenhuma afiliação encontrada (esperado: '1Instituição, Cidade, Estado, País.').")
    problems = []
    for a in affs:
        parts = [x.strip() for x in re.split(r",|\s-\s|/", a) if x.strip()]
        idx = next((i for i, x in enumerate(parts) if x in UF_NAMES or x.upper() in UF_SIGLAS), None)
        if idx is None or not has_uf(a):
            problems.append(f"sem UF: {a}")
        elif idx < 2:
            problems.append(f"sem cidade: {a}")
    return res("fr.afiliacao", desc, "NA" if problems else "A", "; ".join(problems) if problems else f"{len(affs)} afiliação(ões) com cidade e UF")
