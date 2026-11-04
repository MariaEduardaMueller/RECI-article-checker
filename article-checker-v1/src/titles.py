"""TÍTULOS — itens 19, 20, 21, 23 e 112."""
import re
from dataclasses import dataclass

from common import Ctx, fmt_list, is_simple, res, sizes_ok
from document_model import Para, Run
from lang import detect_language

MARKER = re.compile(r"^(ARTIGO\s*ORIGINAL|ORIGINAL\s*ARTICLE|T[ÍI]TULO)\s*$", re.IGNORECASE)
SKIP = re.compile(r"^(DOI:|ORCID|E-mail:|Submetido|Aceite|\d+$)", re.IGNORECASE)
STOP = re.compile(r"ORCID|^\d{1,2}\s*[A-ZÀ-Ú]|^(Autor|Submetido|Aceite|Recebido)", re.IGNORECASE)


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
        out = []
        for txt, runs, p in cands:
            lang = detect_language(txt) if len(txt.split()) > 2 else None
            # PDF: linhas de quebra automática do mesmo título (mesmo idioma ou linha curta) são unidas
            if out and p.line_runs and (lang is None or lang == out[-1][3]):
                prev = out[-1]
                out[-1] = (prev[0] + " " + txt, prev[1] + runs, prev[2], prev[3] or lang)
            else:
                out.append((txt, runs, p, lang))
        return [TitleLine(t, r, p) for t, r, p, _ in out[:3]]
    return ctx.memo("titles", build)


def _issues_for(tl: TitleLine, exact: bool, want_bold: bool) -> list[str]:
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
    if is_simple(tl.para, exact) is False:
        issues.append(f"espaçamento entre linhas {tl.para.line_spacing:g} (esperado simples)")
    return issues


def item_19(ctx: Ctx):
    desc = "Inédito, curto, claro e conciso, identifica o conteúdo do manuscrito, com no máximo 15 palavras"
    tls = title_lines(ctx)
    if not tls:
        return res(19, desc, "NA", "Títulos não encontrados no início do manuscrito")
    over = []
    for i, t in enumerate(tls, 1):
        n = len(re.findall(r"\b\w+\b", re.sub(r"(\w)-(\w)", r"\1_\2", t.text)))
        if n > 15:
            over.append(f"Título {i} ({detect_language(t.text) or 'idioma desconhecido'}): {n} palavras")
    if over:
        return res(19, desc, "NA", "Excedem 15 palavras: " + "; ".join(over))
    return res(19, desc, "A", f"Todos os títulos têm no máximo 15 palavras ({len(tls)} verificados). Ineditismo deve ser conferido manualmente.")


def item_20(ctx: Ctx):
    desc = "Título principal em negrito, centralizado, fonte tamanho 12, espaçamento simples"
    tls = title_lines(ctx)
    if not tls:
        return res(20, desc, "NA", "Título principal não encontrado")
    issues = _issues_for(tls[0], ctx.doc.exact, True)
    return res(20, desc, "NA" if issues else "A", ("Título principal: " + "; ".join(issues)) if issues else "Título principal corretamente formatado")


def item_21(ctx: Ctx):
    desc = "Títulos secundários em itálico, centralizados, fonte tamanho 12, espaçamento simples"
    tls = title_lines(ctx)
    if len(tls) < 2:
        return res(21, desc, "NA", "Títulos secundários não encontrados (esperados 2: inglês e espanhol)")
    msgs = []
    for i, t in enumerate(tls[1:3], 2):
        iss = _issues_for(t, ctx.doc.exact, False)
        if iss:
            msgs.append(f"Título {i}: " + "; ".join(iss))
    return res(21, desc, "NA" if msgs else "A", "; ".join(msgs) if msgs else f"{len(tls) - 1} título(s) secundário(s) corretamente formatado(s)")


def item_23(ctx: Ctx):
    desc = "Títulos nos três idiomas (português, inglês e espanhol), um abaixo do outro"
    tls = title_lines(ctx)
    if not tls:
        return res(23, desc, "NA", "Títulos não encontrados")
    langs = [detect_language(t.text) for t in tls]
    found = {l for l in langs if l}
    required = {"portuguese", "english", "spanish"}
    if found >= required:
        order = [l for l in langs if l]
        note = "" if order[:3] == ["portuguese", "english", "spanish"] else f" (ordem encontrada: {', '.join(order)})"
        return res(23, desc, "A", f"Títulos nos três idiomas{note}")
    if len(found) >= 2:
        return res(23, desc, "AP", f"Encontrados: {', '.join(sorted(found))}. Faltando: {', '.join(sorted(required - found))}")
    return res(23, desc, "NA", f"Idiomas detectados: {', '.join(sorted(found)) or 'nenhum'}")


def item_112(ctx: Ctx):
    desc = "Títulos com apenas a primeira letra em maiúsculo"
    tls = title_lines(ctx)
    if not tls:
        return res(112, desc, "-", "Títulos não encontrados")
    bad, warn = [], []
    for i, t in enumerate(tls, 1):
        if t.text.isupper():
            bad.append(f"Título {i}: todo em maiúsculas")
            continue
        words = t.text.split()
        caps = []
        for j, w in enumerate(words[1:], 1):
            prev = words[j - 1]
            if prev.endswith((":", "?", "!")):
                continue
            clean = re.sub(r"[^\wÀ-ÿ]", "", w)
            if len(clean) >= 3 and clean[0].isupper() and not clean.isupper():
                caps.append(clean)
        n_content = max(1, sum(1 for w in words[1:] if len(re.sub(r"[^\wÀ-ÿ]", "", w)) >= 4))
        if len(caps) >= 3 and len(caps) / n_content >= 0.5:
            bad.append(f"Título {i}: palavras com inicial maiúscula ({fmt_list(caps, 4, ', ')})")
        elif len(caps) > 2:
            warn.append(f"Título {i}: verificar maiúsculas ({fmt_list(caps, 4, ', ')})")
    if bad:
        return res(112, desc, "NA", "; ".join(bad + warn) + ". (Nomes próprios e siglas são aceitos.)")
    if warn:
        return res(112, desc, "AP", "; ".join(warn) + ". Pode ser nome próprio (ex.: nome de unidade/instituição); confirme.")
    return res(112, desc, "A", "Títulos com apenas a primeira letra em maiúsculo (exceto nomes próprios/siglas)")
