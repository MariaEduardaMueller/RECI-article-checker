"""TÍTULO DO MANUSCRITO — 15 palavras, três idiomas, formatação, idioma do 1º título e maiúsculas."""
import re
from dataclasses import dataclass

from common import Ctx, fmt_list, is_simple, note, res, sizes_ok
from document_model import Para, Run
from lang import detect_language

MARKER = re.compile(r"^(ARTIGO\s*ORIGINAL|ORIGINAL\s*ARTICLE|T[ÍI]TULO)\s*$", re.IGNORECASE)
SKIP = re.compile(r"^(DOI:|ORCID|E-mail:|Submetido|Aceite|\d+$)", re.IGNORECASE)
STOP = re.compile(r"ORCID|^\d{1,2}\s*[A-ZÀ-Ú]|^(Autor|Submetido|Aceite|Recebido)", re.IGNORECASE)
LANG_PT = {"portuguese": "português", "english": "inglês", "spanish": "espanhol"}


@dataclass
class TitleLine:
    text: str
    runs: list[Run]
    para: Para


def title_lines(ctx: Ctx) -> list[TitleLine]:
    def build():
        front = ctx.sections.content.get("FRONT", [])
        started = not any(MARKER.match(p.stripped) for p in front)
        cands, done = [], False
        for p in front:
            t = p.stripped
            if not t:
                continue
            if MARKER.match(t):
                started = True
                continue
            if not started or SKIP.match(t):
                continue
            for line in p.visual_lines():
                txt = "".join(r.text for r in line).strip()
                if not txt:
                    continue
                if cands and STOP.search(txt):
                    done = True
                    break
                if SKIP.match(txt) or re.search(r"ORCID|@", txt):
                    continue
                cands.append((txt, list(line), p))
            if done:
                break
        return [TitleLine(t, r, p) for t, r, p in cands[:3]]
    return ctx.memo("titles", build)


def _case_issue(text: str):
    """Apenas a primeira letra em maiúsculo (exceto nomes próprios/siglas). Devolve mensagem ou None."""
    if text.isupper():
        return "todo em maiúsculas"
    words = text.split()
    caps = []
    for j, w in enumerate(words[1:], 1):
        if words[j - 1].endswith((":", "?", "!")):
            continue
        clean = re.sub(r"[^\wÀ-ÿ]", "", w)
        if len(clean) >= 3 and clean[0].isupper() and not clean.isupper():
            caps.append(clean)
    n_content = max(1, sum(1 for w in words[1:] if len(re.sub(r"[^\wÀ-ÿ]", "", w)) >= 4))
    if len(caps) >= 3 and len(caps) / n_content >= 0.5:
        return f"palavras com inicial maiúscula ({fmt_list(caps, 4, ', ')}) — apenas a primeira letra deve ser maiúscula (exceto nomes próprios e siglas)"
    return None


def _issues_for(tl: TitleLine, want_bold: bool) -> list[str]:
    issues = []
    vis = [r for r in tl.runs if r.text.strip()]
    bold = all(r.bold for r in vis)
    italic = all(r.italic for r in vis)
    if want_bold:
        if not bold:
            issues.append("não está em negrito")
    else:
        if bold:
            issues.append("está em negrito")
        if not italic:
            issues.append("não está em itálico")
    if tl.para.align != "center":
        issues.append("não está centralizado")
    sizes = {r.size for r in vis if r.size and not r.superscript}
    if sizes and not sizes_ok(sizes, 12):
        issues.append(f"fonte {'/'.join(f'{s:g}' for s in sorted(sizes))}pt (esperado 12pt)")
    if is_simple(tl.para) is False:
        issues.append(f"espaçamento entre linhas {tl.para.line_spacing:g} (esperado simples)")
    c = _case_issue(tl.text)
    if c:
        issues.append(c)
    return issues


def item_ti_max15(ctx: Ctx):
    desc = "Inédito, curto, claro e conciso, identifica o conteúdo do manuscrito, com no máximo 15 palavras"
    tls = title_lines(ctx)
    if not tls:
        return res("ti.max15", desc, "NA", "Títulos não encontrados no início do manuscrito")
    over, notes = [], []
    for i, t in enumerate(tls, 1):
        n = len(re.findall(r"\b\w+\b", re.sub(r"(\w)-(\w)", r"\1_\2", t.text)))
        if n > 15:
            over.append(f"Título {i} ({LANG_PT.get(detect_language(t.text), 'idioma desconhecido')}): {n} palavras")
            notes.append(note(t.para, f"Título com {n} palavras; o máximo é 15. Reduza {n - 15} palavra(s)."))
    if over:
        return res("ti.max15", desc, "NA", "Excedem 15 palavras: " + "; ".join(over), notes)
    return res("ti.max15", desc, "A", f"Todos os títulos têm no máximo 15 palavras ({len(tls)} verificados). Ineditismo e clareza devem ser conferidos manualmente.")


def item_ti_idiomas(ctx: Ctx):
    desc = "Títulos nos três idiomas (português, inglês e espanhol), um abaixo do outro"
    tls = title_lines(ctx)
    if not tls:
        return res("ti.idiomas", desc, "NA", "Títulos não encontrados")
    langs = [detect_language(t.text) for t in tls]
    found = {l for l in langs if l}
    required = {"portuguese", "english", "spanish"}
    if found >= required:
        return res("ti.idiomas", desc, "A", "Títulos nos três idiomas: " + ", ".join(LANG_PT.get(l, "?") for l in langs))
    miss = ", ".join(LANG_PT[l] for l in sorted(required - found))
    nt = [note(tls[-1].para, f"Faltam os títulos em: {miss}. Inclua os três títulos (português, inglês e espanhol), um abaixo do outro.")]
    if len(found) >= 2:
        return res("ti.idiomas", desc, "AP", f"Encontrados: {', '.join(LANG_PT[l] for l in sorted(found))}. Faltando: {miss}", nt)
    return res("ti.idiomas", desc, "NA", f"Idiomas detectados: {', '.join(LANG_PT[l] for l in sorted(found)) or 'nenhum'}; faltando: {miss}", nt)


def item_ti_principal(ctx: Ctx):
    desc = "Título principal em negrito, centralizado, fonte tamanho 12, espaçamento simples e apenas a primeira letra em maiúsculo"
    tls = title_lines(ctx)
    if not tls:
        return res("ti.principal", desc, "NA", "Título principal não encontrado")
    issues = _issues_for(tls[0], True)
    if not issues:
        return res("ti.principal", desc, "A", "Título principal corretamente formatado")
    return res("ti.principal", desc, "NA", f"Título principal ({ctx.where(tls[0].para)}): " + "; ".join(issues),
               [note(tls[0].para, "Título principal: " + "; ".join(issues) + ".")])


def item_ti_idioma_trabalho(ctx: Ctx):
    desc = "O primeiro título apresentado deve ser do mesmo idioma do trabalho"
    tls = title_lines(ctx)
    body = " ".join(p.stripped for k in ("INTRODUCTION", "METHODS") for p in ctx.sections.get(k))[:3000]
    if not tls or not body:
        return res("ti.idioma_trabalho", desc, "-", "Título ou corpo do texto não encontrados")
    work, first = detect_language(body), detect_language(tls[0].text)
    if not first or not work:
        return res("ti.idioma_trabalho", desc, "-", "Idioma não pôde ser determinado")
    if first == work:
        return res("ti.idioma_trabalho", desc, "A", f"Primeiro título e texto em {LANG_PT[work]}")
    return res("ti.idioma_trabalho", desc, "NA", f"O texto está em {LANG_PT[work]}, mas o primeiro título está em {LANG_PT[first]}",
               [note(tls[0].para, f"O primeiro título deve estar no idioma do trabalho ({LANG_PT[work]}).")])


def item_ti_secundarios(ctx: Ctx):
    desc = "Títulos secundários nos diferentes idiomas em itálico, centralizado, fonte tamanho 12, espaçamento simples e apenas a primeira letra em maiúsculo"
    tls = title_lines(ctx)
    if len(tls) < 2:
        return res("ti.secundarios", desc, "NA", "Títulos secundários não encontrados (esperados 2: inglês e espanhol)")
    msgs, notes = [], []
    for i, t in enumerate(tls[1:3], 2):
        iss = _issues_for(t, False)
        if iss:
            msgs.append(f"Título {i} ({ctx.where(t.para)}): " + "; ".join(iss))
            notes.append(note(t.para, f"Título {i}: " + "; ".join(iss) + "."))
    if msgs:
        return res("ti.secundarios", desc, "NA", " | ".join(msgs), notes)
    return res("ti.secundarios", desc, "A", f"{len(tls) - 1} título(s) secundário(s) corretamente formatado(s)")


def item_ti_plataforma(ctx: Ctx):
    desc = "O título do manuscrito foi cadastrado em inglês na plataforma, com apenas a primeira letra em maiúsculo"
    return res("ti.plataforma", desc, "SKIP", "O cadastro do título na plataforma é conferido pela equipe RECI no sistema (Publicação > Títulos).")
