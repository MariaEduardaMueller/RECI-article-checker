"""Revisão por IA (Ollama) dos itens que antes eram "verificar manualmente" + ortografia.

Política de combinação com as verificações determinísticas:
 * item sem resultado automático ("-")  -> a IA define o status (A/AP/NA), com justificativa e trechos;
 * item já avaliado pelo código          -> a IA só REBAIXA (A -> AP) quando achar problemas e acrescenta a justificativa;
 * IA indisponível                       -> nada muda (itens continuam "Verificar manualmente").
Todas as respostas da IA são marcadas com "[IA]" para o avaliador saber a origem.
"""
import json
import re

from common import Ctx, fmt_list, n_words, note

SYSTEM = ("Você é revisor científico da Revista de Epidemiologia e Controle de Infecção (RECI). "
          "Avalie o texto com rigor, sem inventar trechos. Responda SOMENTE com JSON válido.")
MAX_CHARS = 9000
VALID = {"A", "AP", "NA"}

FORMAT = ('Responda em JSON: {"status": "A" (atende) | "AP" (atende parcialmente) | "NA" (não atende), '
          '"justificativa": "1 a 2 frases objetivas", '
          '"problemas": [{"trecho": "trecho EXATO copiado do texto (até 20 palavras) ou vazio", "sugestao": "o que o autor deve alterar"}]}')


def llm_json(ctx: Ctx, prompt: str) -> dict | None:
    """Chama o modelo local; devolve None se a IA estiver indisponível (e não tenta de novo)."""
    if not ctx.use_llm or ctx.cache.get("ai_down"):
        return None
    try:
        import ollama  # type: ignore
        r = ollama.chat(model=ctx.llm_model, format="json",
                        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt[:MAX_CHARS + 3000]}],
                        options={"temperature": 0.0, "num_ctx": 8192})
        data = json.loads(re.search(r"\{[\s\S]*\}", r["message"]["content"]).group(0))
        ctx.cache["ai_calls"] = ctx.cache.get("ai_calls", 0) + 1
        return data if isinstance(data, dict) else None
    except Exception as e:  # noqa: BLE001
        ctx.cache["ai_down"] = True
        ctx.cache["ai_error"] = f"{type(e).__name__}: {e}"
        return None


def _status(data: dict) -> str | None:
    s = str(data.get("status", "")).strip().upper().replace("Ã", "A")
    return s if s in VALID else None


def _locate(paras, trecho: str):
    """(parágrafo, início, fim) do trecho citado pela IA, ou None."""
    t = " ".join(str(trecho).split())
    if len(t) < 4:
        return None
    for p in paras:
        i = p.text.find(t)
        if i >= 0:
            return p, i, i + len(t)
    low = t.lower()
    for p in paras:
        i = p.text.lower().find(low)
        if i >= 0:
            return p, i, i + len(t)
    return None


def _merge(ctx: Ctx, r: dict, data: dict, paras, label: str, only_downgrade: bool = False):
    st = _status(data)
    if st is None:
        return
    just = str(data.get("justificativa", "")).strip()
    probs = [x for x in (data.get("problemas") or []) if isinstance(x, dict) and (x.get("sugestao") or x.get("trecho"))]
    new_notes = []
    for x in probs[:4]:
        loc = _locate(paras, x.get("trecho", "")) if paras else None
        msg = f"[IA] {label}: {x.get('sugestao', '').strip()}".strip()
        if loc:
            new_notes.append(note(loc[0], msg, loc[1], loc[2]))
        elif paras and st != "A":
            new_notes.append(note(paras[0], msg))
    txt = f"[IA] {just}" if just else "[IA] avaliado"
    if probs:
        txt += " Sugestões: " + fmt_list([str(x.get("sugestao", "")).strip() for x in probs if x.get("sugestao")], 3)
    cur = r["status"]
    if cur == "-" and not only_downgrade:
        r["status"] = st
        r["comments"] = txt
        r["notes"] = r.get("notes", []) + (new_notes if st != "A" else [])
    elif cur == "-":
        r["comments"] = (r["comments"] + " " + txt).strip()
    elif cur in ("A", "AP", "NA"):
        if st in ("AP", "NA") and cur == "A":
            r["status"] = "AP"
        r["comments"] = (r["comments"] + " | " + txt).strip(" |")
        if st != "A":
            r["notes"] = r.get("notes", []) + new_notes


# ------------------------------------------------------------------------------------------------
def _sec(ctx, *keys):
    return "\n".join(f"[{i + 1}] {p.stripped}" for k in keys for i, p in enumerate(ctx.sections.get(k)))


def _prompt(criterio: str, contexto: str, texto: str) -> str:
    return (f"CRITÉRIO DA RECI: {criterio}\n{contexto}\nTEXTO A AVALIAR:\n\"\"\"{texto[:MAX_CHARS]}\"\"\"\n{FORMAT}")


def _abstract_objective(ctx):
    full = " ".join(p.stripped for p in ctx.sections.get("RESUMO"))
    m = re.search(r"Justificativa e Objetivos:(.*?)(?:Métodos:|$)", full, re.S | re.I)
    return (m.group(1) if m else full)[:600].strip()


def _specs(ctx: Ctx):
    S = ctx.sections
    methods_head = ctx.sections.text("METHODS")[:900]
    from titles import title_lines
    titles = " | ".join(t.text for t in title_lines(ctx))
    descr = " | ".join(p.stripped for k in ("RESUMO", "ABSTRACT", "RESUMEN") for p in S.get(k)
                       if re.match(r"\s*(Descritores|Keywords|Palabras)", p.stripped, re.I))
    tables = "\n".join(" ; ".join(r) for t in ctx.doc.tables[:4] for r in t.rows[:14])
    refs = "\n".join(p.stripped for p in S.get("REFERENCES")[:30])
    return {
        "in.breve": (("INTRODUCTION",), _prompt(
            "A Introdução deve ser BREVE e conter revisão da literatura, justificativa e objetivo do estudo. Verifique se cada elemento está presente e se o texto é conciso (sem desvios).",
            "", _sec(ctx, "INTRODUCTION")), "Introdução", False),
        "in.objetivo": (("INTRODUCTION",), _prompt(
            "O objetivo (último parágrafo da Introdução) deve ser coerente com a proposta do estudo descrita nos Métodos e idêntico ao do resumo.",
            f"OBJETIVO DO RESUMO: {_abstract_objective(ctx)}\nINÍCIO DOS MÉTODOS: {methods_head}", _sec(ctx, "INTRODUCTION")[-1800:]), "Objetivo", True),
        "me.objetiva": (("METHODS",), _prompt(
            "Os Métodos devem ser descritos de forma objetiva e completa: delineamento, local, população, critérios de seleção, coleta de dados, variáveis, análise e ética. Indique o que falta, está confuso ou prolixo.",
            "", _sec(ctx, "METHODS")), "Métodos", False),
        "rs.sequencia": (("RESULTS",), _prompt(
            "Os Resultados devem estar em sequência lógica (do geral ao específico, acompanhando os objetivos/métodos), sem interpretação ou discussão. Aponte desvios.",
            f"OBJETIVO: {_abstract_objective(ctx)}", _sec(ctx, "RESULTS")), "Resultados", False),
        "di.literatura": (("DISCUSSION",), _prompt(
            "A Discussão deve comparar os resultados com a literatura (com citações numéricas) e discuti-los adequadamente (interpretação, limitações). Aponte trechos sem comparação com a literatura.",
            "", _sec(ctx, "DISCUSSION")), "Discussão", False),
        "co.incorporada": (("DISCUSSION",), _prompt(
            "O último parágrafo da Discussão deve conter a conclusão e ela deve responder aos objetivos do estudo.",
            f"OBJETIVO: {_abstract_objective(ctx)}", _sec(ctx, "CONCLUSION") or _sec(ctx, "DISCUSSION")[-1500:]), "Conclusão", True),
        "ti.max15": (("FRONT",), _prompt(
            "O título deve ser curto, claro, conciso e identificar o conteúdo do manuscrito (o ineditismo não pode ser avaliado aqui).",
            f"OBJETIVO: {_abstract_objective(ctx)}", titles), "Título", True),
        "de.quantidade": (("RESUMO",), _prompt(
            "Os descritores devem constar no DeCS/BIREME (equivalentes ao MeSH). Liste em 'problemas' (campo 'trecho' = o termo) apenas os termos que provavelmente NÃO são descritores oficiais.",
            "", descr), "Descritores", True) if descr else None,
        "tb.editaveis": (("RESULTS",), _prompt(
            "As tabelas devem transmitir os dados de forma clara: cabeçalhos explícitos, unidades, categorias compreensíveis, N (%) padronizados.",
            "", tables), "Tabelas", True) if tables else None,
        "rf.vancouver": (("REFERENCES",), _prompt(
            "Os títulos de periódicos devem estar abreviados conforme o Index Medicus/MedLine (ex.: Rev Bras Epidemiol; Cad Saude Publica). Liste em 'problemas' (trecho = nome do periódico) os que estão por extenso ou fora do padrão.",
            "", refs), "Referências", True) if refs else None,
    }


def review(ctx: Ctx, by_id: dict) -> None:
    for iid, spec in _specs(ctx).items():
        r = by_id.get(iid)
        if spec is None or r is None or r["status"] == "NSA":
            continue
        keys, prompt, label, only_down = spec
        if not prompt.strip():
            continue
        data = llm_json(ctx, prompt)
        if data is None:
            return
        paras = [p for k in keys for p in ctx.sections.get(k)] if keys != ("FRONT",) else ctx.sections.get("FRONT")
        if iid == "tb.editaveis":
            paras = ctx.sections.get("RESULTS")
        _merge(ctx, r, data, paras, label, only_down)


# ------------------------------------------------------------------------------------------------
SPELL_PROMPT = ("Revise APENAS ortografia oficial (acentuação, grafia, concordância, regência, pontuação) do texto abaixo, no idioma do texto. "
                "Liste somente erros reais e inequívocos; não reescreva o estilo. "
                'Responda em JSON: {"erros": [{"trecho": "palavra/expressão EXATA com erro", "correcao": "forma correta", "explicacao": "motivo curto"}]}\n'
                'TEXTO:\n"""%s"""')


def spelling(ctx: Ctx, by_id: dict, max_notes: int = 30) -> None:
    r = by_id.get("fg.fonte")
    if r is None:
        return
    paras = [p for k in ("RESUMO", "INTRODUCTION", "METHODS", "RESULTS", "DISCUSSION") for p in ctx.sections.get(k) if n_words(p.stripped) >= 6]
    chunks, cur, size = [], [], 0
    for p in paras:
        if size + len(p.stripped) > 2400 and cur:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(p)
        size += len(p.stripped)
    if cur:
        chunks.append(cur)
    found = []
    for ch in chunks:
        data = llm_json(ctx, SPELL_PROMPT % "\n".join(p.stripped for p in ch))
        if data is None:
            return
        for e in (data.get("erros") or []):
            if not isinstance(e, dict) or not e.get("trecho") or not e.get("correcao") or str(e["trecho"]).strip() == str(e["correcao"]).strip():
                continue
            loc = _locate(ch, e["trecho"])
            if loc and len(found) < max_notes:
                found.append((loc, e))
    if not found:
        r["comments"] = (r["comments"].replace(" Ortografia oficial não é verificada automaticamente.", "") + " [IA] Ortografia: nenhum erro evidente encontrado.").strip()
        return
    for (p, s, e_), e in found:
        r["notes"] = r.get("notes", []) + [note(p, f"[IA] Ortografia/gramática: “{e['trecho']}” → “{e['correcao']}”" + (f" ({e.get('explicacao')})" if e.get("explicacao") else ""), s, e_)]
    ex = fmt_list([f"“{e['trecho']}”→“{e['correcao']}” ({ctx.where(loc[0])})" for loc, e in found], 3)
    r["comments"] = (r["comments"].replace(" Ortografia oficial não é verificada automaticamente.", "") + f" [IA] {len(found)} possível(is) erro(s) de ortografia/gramática: {ex}").strip()
    if r["status"] == "A":
        r["status"] = "AP"


def apply(ctx: Ctx, cat: dict, sections: list, spell: bool = True) -> None:
    """Aplica a revisão por IA sobre os resultados já calculados."""
    by_id = {r["item"]: r for _, rs in sections for r in rs}
    if not ctx.use_llm:
        return
    review(ctx, by_id)
    if spell:
        spelling(ctx, by_id)
