"""MÉTODO — delineamento, cenário, população, critérios, fonte, período e análise.
Usa LLM local (Ollama) quando disponível; senão, verificação por palavras-chave."""
import json
import re

from common import DEFAULT_MODEL, Ctx, note, res

PROMPT_METHODS = """
ATUE COMO UM ESPECIALISTA EM METODOLOGIA CIENTÍFICA.
Analise a seção MÉTODOS do texto abaixo e extraia os dados solicitados em formato JSON.

TEXTO MÉTODOS:
\"\"\"{metodos}\"\"\"

DIRETRIZES: respostas bem curtas; se a informação existir, transcreva detalhes, datas e nomes exatos citados no texto.
STATUS: "A" se a informação estiver presente (mesmo por sinônimos) e "NA" se totalmente ausente.

GERE APENAS O JSON ABAIXO:
{{
 "1": {{"status": "A ou NA", "comentario": "Termo EXATO usado pelos autores para o delineamento, entre aspas. PROIBIDO inferir."}},
 "2": {{"status": "A ou NA", "comentario": "Onde o estudo aconteceu: país, região, cidades, tipo de instituição."}},
 "3": {{"status": "A ou NA", "comentario": "Quem ou o que foi estudado."}},
 "4": {{"status": "A ou NA", "comentario": "Critérios de inclusão/exclusão. Uso da totalidade dos registros de uma base conta como A."}},
 "5": {{"status": "A ou NA", "comentario": "Nome EXATO dos sistemas/instrumentos citados."}},
 "6": {{"status": "A ou NA", "comentario": "Apenas as datas/intervalos citados."}},
 "7": {{"status": "A ou NA", "comentario": "Como os dados foram tratados. Análise descritiva TAMBÉM conta (A)."}}
}}
"""

IDS = {"1": ("me.delineamento", "Delineamento/período de realização do estudo", "o delineamento do estudo (ex.: “estudo transversal/ecológico/de coorte...”) e o período de realização"),
       "2": ("me.cenario", "Cenário estudado", "o cenário estudado (local, país/região, tipo de instituição)"),
       "3": ("me.populacao", "População", "a população estudada"),
       "4": ("me.criterios", "Critérios de seleção (inclusão/exclusão)", "os critérios de seleção (inclusão/exclusão)"),
       "5": ("me.fonte", "Fonte de dados", "a fonte de dados (sistema, instrumento ou base utilizada)"),
       "6": ("me.periodo", "Período de coleta dos dados", "o período de coleta dos dados (datas ou intervalo)"),
       "7": ("me.analise", "Tipo de análise realizada", "o tipo de análise realizada (descritiva, testes estatísticos, software)")}

KEYWORDS = {
    "1": r"estudo\s+(?:\w+\s+){0,3}?(?:ecol[óo]gico|transversal|de coorte|coorte|caso-controle|descritivo|observacional|retrospectivo|prospectivo|qualitativo|quantitativo|experimental|epidemiol[óo]gico|de base populacional)|s[ée]rie temporal|ensaio cl[ií]nico|revis[ãa]o (?:integrativa|sistem[áa]tica|de escopo|narrativa)|pesquisa (?:qualitativa|quantitativa|documental|descritiva)|relato de (?:caso|experi[êe]ncia)|time-series",
    "2": r"realizad[oa]s?\s+(?:em|no|na|nos|nas)\s+[^.]{3,80}|hospital|unidade[s]? de|munic[íi]pio|estado d[eo]|regi[ãa]o|pa[íi]s|ambulat[óo]rio|UBS|servi[çc]o de|institui[çc][ãa]o|cl[íi]nica|escola|Brasil",
    "3": r"popula[çc][ãa]o|amostra|participantes|pacientes|indiv[íi]duos|crian[çc]as|idosos|adolescentes|gestantes|usu[áa]rios|prontu[áa]rios|registros|casos (?:notificados|confirmados)|mulheres|homens|profissionais",
    "4": r"crit[ée]rios? de (?:inclus[ãa]o|exclus[ãa]o|sele[çc][ãa]o|elegibilidade)|foram (?:inclu[íi]dos|exclu[íi]dos)|inclu[íi]ram-se|exclu[íi]ram-se|todos os (?:registros|casos|dados|esquemas|[óo]bitos)|totalidade (?:dos|de)",
    "5": r"dados (?:foram |foi )?(?:obtid|coletad|extra[íi]d|levantad|dispon[íi]ve)\w*|fonte[s]? de dados|banco de dados|base de dados|SINAN|SIM\b|SINASC|SI-PNI|DATASUS|SIH|prontu[áa]rio|question[áa]rio|entrevista|formul[áa]rio|sistema de informa[çc][ãa]o",
    "6": r"(?:19|20)\d{2}\s*(?:a|e|até|-|–)\s*(?:19|20)\d{2}|(?:janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+(?:19|20)\d{2}|entre\s+(?:19|20)\d{2}|em\s+(?:19|20)\d{2}|\d+\s+(?:meses|dias|semanas)",
    "7": r"an[áa]lise|teste[s]?\s+\w+|qui-quadrado|regress[ãa]o|SPSS|Stata|Epi\s?Info|Excel|estat[íi]stic\w+|frequ[êe]ncia|taxa[s]?|raz[ãa]o|odds|joinpoint|m[ée]dia|mediana|desvio|percentual|preval[êe]ncia|incid[êe]ncia|descritiv\w+|p\s*[<=≤]",
}


EMPTY_ANSWER = re.compile(r"n[ãa]o\s+(?:foi\s+|est[áa]\s+|h[áa]\s+)?(?:especificad|informad|mencionad|descrit|encontrad|consta|dispon[ií]vel|apresentad|cita|identificad)|"
                          r"sem\s+(?:informa|men[cç])|n/?a\b|nenhum[ao]?\s+(?:informa|crit|dado)|n[ãa]o\s+se\s+aplica|ausente|inexistente", re.IGNORECASE)


def _llm(ctx: Ctx, text: str):
    try:
        import ollama  # type: ignore
        r = ollama.chat(model=ctx.llm_model, format="json", messages=[{"role": "user", "content": PROMPT_METHODS.format(metodos=text)}],
                        options={"temperature": 0.0, "num_ctx": 8192})
        return json.loads(re.search(r"\{[\s\S]*\}", r["message"]["content"]).group(0))
    except Exception:
        return None


def methods_items(ctx: Ctx) -> dict:
    def build():
        M = ctx.sections.get("METHODS")
        text = ctx.sections.text("METHODS")
        out = {}
        if not text.strip():
            for k, (iid, desc, what) in IDS.items():
                out[iid] = res(iid, desc, "NA", "Seção de Métodos não encontrada", [note(None, "Seção de Métodos não encontrada.")])
            return out
        data = _llm(ctx, text) if ctx.use_llm else None
        for k, (iid, desc, what) in IDS.items():
            miss_note = [note(M[0], f"Informe {what}.")]
            if data and isinstance(data.get(k), dict) and data[k].get("status") in ("A", "NA"):
                st, c = data[k]["status"], str(data[k].get("comentario", ""))
                if st == "A" and (not c.strip() or EMPTY_ANSWER.search(c)):     # modelos pequenos dizem "A" e "Não especificado"
                    st = "NA"
                out[iid] = res(iid, desc, st, f"[LLM] {c}" + ("" if st == "A" else f" — informe {what}"), [] if st == "A" else miss_note)
            else:
                hits = [m.group(0).strip() for m in re.finditer(KEYWORDS[k], text, re.IGNORECASE) if len(m.group(0).strip()) > 1]
                if k == "6":
                    hits = [h for h in hits if re.search(r"(?:19|20)\d{2}|meses|dias|semanas", h)]
                if hits:
                    out[iid] = res(iid, desc, "A", f"[palavras-chave] trecho encontrado: “{hits[0][:60]}”")
                else:
                    out[iid] = res(iid, desc, "NA", f"[palavras-chave] não identificado em Métodos — informe {what}", miss_note)
        return out
    return ctx.memo("methods_items", build)


def make_item(iid):
    return lambda ctx: methods_items(ctx)[iid]


def item_me_objetiva(ctx: Ctx):
    return res("me.objetiva", "As informações devem ser descritas de forma objetiva e completa", "-", "Avaliação manual (objetividade e completude dos Métodos)")
