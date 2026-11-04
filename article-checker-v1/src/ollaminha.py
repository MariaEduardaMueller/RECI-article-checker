"""Itens 36 a 42 (Métodos) — validação semântica com LLM local (Ollama). Opcional."""
import json
import re

from common import DEFAULT_MODEL, Ctx, res

PROMPT_METHODS = """
ATUE COMO UM ESPECIALISTA EM METODOLOGIA CIENTÍFICA.
Analise a seção MÉTODOS do texto abaixo e extraia os dados solicitados em formato JSON.

TEXTO MÉTODOS:
\"\"\"{metodos}\"\"\"

DIRETRIZES GERAIS PARA OS COMENTÁRIOS:
- Use respostas bem curtas. Se a informação existir, transcreva detalhes, datas e nomes exatos citados no texto.
- STATUS: "A" (Atende) se a informação estiver presente (mesmo por sinônimos ou descrição de processo) e "NA" (Não Atende) se totalmente ausente.

GERE APENAS O JSON ABAIXO:
{{
 "1": {{"description": "Delineamento", "status": "A ou NA", "comentario": "Termo EXATO usado pelos autores, entre aspas. PROIBIDO inferir classificações não citadas."}},
 "2": {{"description": "Cenário", "status": "A ou NA", "comentario": "Onde o estudo aconteceu: país, região, cidades, tipo de instituição."}},
 "3": {{"description": "População", "status": "A ou NA", "comentario": "Quem ou o que foi estudado."}},
 "4": {{"description": "Critérios de Seleção", "status": "A ou NA", "comentario": "Critérios de inclusão/exclusão. Se o estudo usou a totalidade dos registros de uma base de dados, considere A e escreva: 'Estudo baseou-se na totalidade dos registros da base de dados mencionada'."}},
 "5": {{"description": "Fonte de Dados", "status": "A ou NA", "comentario": "Nome EXATO dos sistemas/instrumentos citados (ex.: SI-PNI, prontuários, questionário)."}},
 "6": {{"description": "Período", "status": "A ou NA", "comentario": "Apenas as datas/intervalos citados (ex.: 'janeiro de 2010 a dezembro de 2020')."}},
 "7": {{"description": "Análise", "status": "A ou NA", "comentario": "Como os dados foram tratados (taxas, comparações, testes). Análise descritiva TAMBÉM conta (A)."}}
}}
"""

MAPPING = {
    "1": (36, "Delineamento"), "2": (37, "Cenário estudado"), "3": (38, "População"),
    "4": (39, "Critérios de seleção (inclusão/exclusão)"), "5": (40, "Fonte de dados"),
    "6": (41, "Período de coleta dos dados"), "7": (42, "Tipo de análise realizada"),
}


def _skipped(msg):
    return [res(n, d, "-", msg) for n, d in MAPPING.values()]


def analyze_methods(methods_text: str, model: str = DEFAULT_MODEL) -> list[dict]:
    try:
        import ollama  # type: ignore
    except ImportError:
        return _skipped("Pacote 'ollama' não instalado (pip install ollama) — itens de Métodos não verificados")
    try:
        r = ollama.chat(model=model, format="json",
                        messages=[{"role": "user", "content": PROMPT_METHODS.format(metodos=methods_text)}],
                        options={"temperature": 0.0, "num_ctx": 8192})
        raw = r["message"]["content"].strip()
        m = re.search(r"\{[\s\S]*\}", raw)
        data = json.loads(m.group(0))
    except Exception as e:                      # servidor indisponível, modelo ausente, JSON inválido...
        return _skipped(f"LLM indisponível ({type(e).__name__}); inicie o Ollama e rode 'ollama pull {model}'")
    out = []
    for k, (n, d) in MAPPING.items():
        v = data.get(k, {}) or {}
        st = v.get("status", "-")
        out.append(res(n, d, st if st in ("A", "NA") else "-", v.get("comentario", "")))
    return out


def methods_items(ctx: Ctx) -> list[dict]:
    def build():
        if not ctx.use_llm:
            return _skipped("Verificação por LLM desativada (--sem-llm)")
        text = ctx.sections.text("METHODS")
        if not text.strip():
            return [res(n, d, "NA", "Seção de Métodos não encontrada") for n, d in MAPPING.values()]
        return analyze_methods(text, ctx.llm_model)
    return ctx.memo("llm", build)


def make_item(n):
    return lambda ctx: next(r for r in methods_items(ctx) if r["item"] == n)
