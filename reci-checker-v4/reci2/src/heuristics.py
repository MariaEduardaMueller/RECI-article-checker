"""Substitutos POR CÓDIGO (sem IA) para itens que antes ficavam em "verificar manualmente".

Medem INDÍCIOS objetivos (citações, expressões de justificativa/comparação, ordem de menções, tamanho de frases, sobreposição
de palavras...). Não avaliam a qualidade científica do texto: por isso os comentários vêm marcados com "[código]" e os
resultados usam A/AP/NA conforme os indícios encontrados. Só preenchem itens que ainda estão em "-" (a IA, quando ligada, tem prioridade).
"""
import re

from body_sections import _sentences, _tokens, find_objective
from citations import PAREN_NUM, superscript_groups
from common import Ctx, fmt_list, n_words, note, strip_accents
from tables_and_figures import KIND, MENTION, _expand

TAG = "[código]"
_JUST = re.compile(r"justific|lacuna|escassez|poucos estudos|pouco se (?:sabe|conhece)|desconhec|carece|necessidade de|relev[aâ]ncia|"
                   r"importante|urgente|ainda n[ãa]o|permanece[m]? (?:incert|pouco)|n[ãa]o est[áa] (?:claro|bem)|surge a (?:quest|necess)", re.I)
_INTERPRET = re.compile(r"\b(?:sugere|sugerindo|sugerem|provavelmente|possivelmente|talvez|em concord[âa]ncia|concordam? com|corrobor\w+|"
                        r"consistente[s]? com|pode(?:m)? ser explicad\w+|isso (?:indica|mostra|reflete)|reflet\w+)\b", re.I)
_COMPARE = re.compile(r"concord|semelhan|similar|diverg|em contraste|contr[aá]rio|corrobor|consistente|em linha com|difere|diferente d|"
                      r"igualmente|assim como|tamb[ée]m (?:observ|encontr|relat)|conforme (?:observ|relat)|achados? (?:de|d[ao]s?)", re.I)

# nomes por extenso de periódicos (devem estar abreviados no padrão Index Medicus/MedLine)
_FULL_JOURNAL_WORDS = re.compile(r"\b(Journal|Revista|International|Brasileira|Brasileiro|Medicine|Medicina|Epidemiology|Epidemiologia|"
                                 r"Infection|Infectious|Diseases?|Research|Clinical|Reviews?|American|Archives)\b")


def _cites(p) -> int:
    return len(superscript_groups(p)) + len(PAREN_NUM.findall(p.text))


def _set(r: dict, status: str, comment: str, notes=None):
    r["status"] = status
    r["comments"] = f"{TAG} {comment}"
    r["notes"] = r.get("notes", []) + (notes or [])


def _grade(problems: list) -> str:
    return "A" if not problems else ("AP" if len(problems) <= 1 else "NA")


# ------------------------------------------------------------------------------------------------
def intro_breve(ctx: Ctx, r: dict):
    paras = ctx.sections.get("INTRODUCTION")
    if not paras:
        return
    text = " ".join(p.stripped for p in paras)
    words, cites = n_words(text), sum(_cites(p) for p in paras)
    probs, notes = [], []
    if words > 800:
        probs.append(f"{words} palavras (introdução extensa; a RECI pede texto breve)")
        notes.append(note(paras[0], f"Introdução com {words} palavras: torne-a mais breve (revisão da literatura, justificativa e objetivo)."))
    if cites < 3:
        probs.append(f"apenas {cites} citação(ões): não há indício de revisão da literatura")
        notes.append(note(paras[0], "A Introdução deve apresentar a revisão da literatura, com citações numéricas."))
    if not _JUST.search(text):
        probs.append("não há expressões de justificativa (ex.: lacuna, relevância, necessidade)")
        notes.append(note(paras[-1], "Explicite a justificativa do estudo (lacuna do conhecimento ou relevância) antes do objetivo."))
    if not find_objective(paras[-1].text)[0]:
        probs.append("objetivo não identificado no último parágrafo")
    long_pars = [p for p in paras if n_words(p.stripped) > 220]
    if long_pars:
        probs.append(f"{len(long_pars)} parágrafo(s) com mais de 220 palavras")
        notes.append(note(long_pars[0], "Parágrafo muito longo: divida ou sintetize."))
    ok = f"{words} palavras, {cites} citações, justificativa e objetivo identificados" if not probs else "; ".join(probs)
    _set(r, _grade(probs), ok + ". (Indícios por código; o conteúdo não é avaliado.)", notes)


def metodos_objetivos(ctx: Ctx, r: dict, by_id: dict):
    paras = ctx.sections.get("METHODS")
    if not paras:
        return
    names = {"me.delineamento": "delineamento", "me.cenario": "cenário", "me.populacao": "população", "me.criterios": "critérios de seleção",
             "me.fonte": "fonte de dados", "me.periodo": "período", "me.analise": "análise", "me.etica": "considerações éticas"}
    missing = [n for k, n in names.items() if k in by_id and by_id[k]["status"] == "NA"]
    probs, notes = [], []
    if missing:
        probs.append("faltam elementos: " + ", ".join(missing))
    long_sent = []
    for p in paras:
        for s in _sentences(p.text):
            if n_words(s) > 50:
                long_sent.append((p, s))
    if long_sent:
        probs.append(f"{len(long_sent)} frase(s) com mais de 50 palavras (pouco objetivas)")
        for p, s in long_sent[:3]:
            i = p.text.find(s[:40])
            notes.append(note(p, f"Frase muito longa ({n_words(s)} palavras): divida para ficar objetiva.", i if i >= 0 else None, (i + len(s)) if i >= 0 else None))
    words = sum(n_words(p.stripped) for p in paras)
    ok = f"{words} palavras; delineamento, cenário, população, critérios, fonte, período, análise e ética identificados" if not probs else "; ".join(probs)
    _set(r, _grade(probs), ok + ". (Indícios por código.)", notes)


def resultados_sequencia(ctx: Ctx, r: dict):
    paras = [p for p in ctx.sections.get("RESULTS") if not re.match(r"^\s*(Tabela|Quadro|Figura|Gr[aá]fico)\s*\d+", p.stripped, re.I)]
    if not paras:
        return
    probs, notes = [], []
    seen = {"tabela": 0, "figura": 0, "gráfico": 0}
    for p in paras:
        for m in MENTION.finditer(p.text):
            kind = KIND[m.group(1).lower().rstrip("s")]
            for n in sorted(_expand(m.group(2))):
                if n > seen[kind] + 1:
                    probs.append(f"{kind} {n} mencionada(o) antes de {kind} {seen[kind] + 1} (ordem das menções)")
                    notes.append(note(p, f"Mencione as {kind}s na ordem numérica: {kind} {seen[kind] + 1} deve aparecer antes da {n}.", m.start(), m.end()))
                seen[kind] = max(seen[kind], n)
    cited = [p for p in paras if _cites(p)]
    if cited:
        probs.append(f"{len(cited)} parágrafo(s) com citação da literatura (Resultados descrevem apenas os achados do estudo)")
        notes += [note(p, "Resultados não devem comparar com a literatura: mova esta citação para a Discussão.") for p in cited[:3]]
    interp = [(p, m) for p in paras for m in _INTERPRET.finditer(p.text)]
    if interp:
        probs.append(f"{len(interp)} expressão(ões) interpretativa(s) nos Resultados (ex.: “{interp[0][1].group(0)}”)")
        notes += [note(p, f"Evite interpretar nos Resultados (“{m.group(0)}”): deixe para a Discussão.", m.start(), m.end()) for p, m in interp[:3]]
    ok = "ordem das menções de tabelas/figuras correta, sem citações da literatura nem interpretações" if not probs else "; ".join(probs[:4])
    _set(r, _grade(probs), ok + ". (Indícios por código; a lógica da narrativa não é avaliada.)", notes)


def discussao_literatura(ctx: Ctx, r: dict):
    paras = [p for p in ctx.sections.get("DISCUSSION") if not re.match(r"^\s*(Tabela|Quadro|Figura|Gr[aá]fico)\s*\d+", p.stripped, re.I)]
    if len(paras) < 2:
        return
    core = paras[:-1]                                   # o último parágrafo é a conclusão
    total = sum(_cites(p) for p in paras)
    without = [p for p in core if _cites(p) == 0 and not re.search(r"limita", p.text, re.I)]
    cues = sum(len(_COMPARE.findall(p.text)) for p in paras)
    probs, notes = [], []
    if total < 5:
        probs.append(f"apenas {total} citação(ões) na Discussão")
    if core and len(without) / len(core) > 0.4:
        probs.append(f"{len(without)}/{len(core)} parágrafos sem nenhuma citação da literatura")
        notes += [note(p, "Este parágrafo não compara os resultados com a literatura (sem citações).") for p in without[:3]]
    if cues < 2:
        probs.append("poucas expressões de comparação (ex.: “semelhante a”, “diverge de”, “em concordância com”)")
    ok = f"{total} citações e {cues} expressões de comparação distribuídas na Discussão" if not probs else "; ".join(probs)
    _set(r, _grade(probs), ok + ". (Indícios por código; a qualidade da discussão não é avaliada.)", notes)


def conclusao_objetivo(ctx: Ctx, r: dict):
    """Conclusão responde ao objetivo? Sobreposição de palavras entre o objetivo e o último parágrafo da Discussão."""
    if r["status"] not in ("A", "AP") or "[código]" in r["comments"]:
        return
    intro, disc = ctx.sections.get("INTRODUCTION"), ctx.sections.get("DISCUSSION")
    if not intro or not disc:
        return
    clause = next((find_objective(p.text)[2] for p in reversed(intro) if find_objective(p.text)[0]), None)
    if not clause:
        return
    a, b = _tokens(clause), _tokens(disc[-1].text)
    cov = len(a & b) / len(a) if a else 1.0
    if cov < 0.15:
        r["comments"] += f" | {TAG} pouca relação entre o objetivo e a conclusão ({cov:.0%} das palavras-chave do objetivo aparecem no último parágrafo)."
        r["notes"] = r.get("notes", []) + [note(disc[-1], f"A conclusão deve responder ao objetivo do estudo (apenas {cov:.0%} de correspondência de termos).")]
        if r["status"] == "A":
            r["status"] = "AP"
    else:
        r["comments"] += f" | {TAG} {cov:.0%} dos termos do objetivo aparecem na conclusão."


def periodicos_abreviados(ctx: Ctx, r: dict):
    """Aponta periódicos que parecem estar por extenso (o padrão é a abreviação do Index Medicus/MedLine)."""
    from references import reference_entries
    if r["status"] not in ("A", "AP") or "[código]" in r["comments"]:
        return
    flagged, notes = [], []
    for ref in reference_entries(ctx):
        parts = [x.strip() for x in re.split(r"\.\s+", ref.text)]
        if len(parts) < 3:
            continue
        journal = parts[2] if len(parts) > 2 else ""
        journal = re.sub(r"\s*\d{4}.*$", "", journal)
        if len(_FULL_JOURNAL_WORDS.findall(journal)) >= 1 and len(journal.split()) >= 3:
            flagged.append(ref.num)
            i = ref.para.text.find(journal)
            notes.append(note(ref.para, f"O periódico parece estar por extenso (“{journal[:60]}”): use a abreviação do Index Medicus/MedLine.",
                              i if i >= 0 else None, (i + len(journal)) if i >= 0 else None))
    if flagged:
        r["comments"] += f" | {TAG} periódico possivelmente por extenso nas refs {fmt_list(flagged, 8, ', ')}."
        r["notes"] = r.get("notes", []) + notes[:8]
        if r["status"] == "A":
            r["status"] = "AP"
    else:
        r["comments"] += f" | {TAG} nenhum periódico por extenso detectado (conferência final no Index Medicus)."


def apply(ctx: Ctx, cat: dict, sections: list) -> None:
    """Preenche por código o que ainda estiver como "verificar manualmente" e acrescenta checagens objetivas."""
    by_id = {r["item"]: r for _, rs in sections for r in rs}
    todo = {"in.breve": lambda r: intro_breve(ctx, r),
            "me.objetiva": lambda r: metodos_objetivos(ctx, r, by_id),
            "rs.sequencia": lambda r: resultados_sequencia(ctx, r),
            "di.literatura": lambda r: discussao_literatura(ctx, r)}
    for iid, fn in todo.items():
        r = by_id.get(iid)
        if r is not None and r["status"] == "-":
            fn(r)
    if "co.incorporada" in by_id:
        conclusao_objetivo(ctx, by_id["co.incorporada"])
    if "rf.vancouver" in by_id:
        periodicos_abreviados(ctx, by_id["rf.vancouver"])
