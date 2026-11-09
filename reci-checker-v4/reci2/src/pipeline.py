"""Fluxo completo reutilizável (terminal e site): verifica o manuscrito e gera Checklist.docx, artigo comentado e JSON."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

import ai_review
import heuristics
from annotate import write_commented
from checklist import run_all
from checklist_docx import fill_checklist
from common import DEFAULT_MODEL, Ctx
from document_model import load_document
from render import export_json, summary

TEMPLATE_NAMES = ("Checklist_modelo.docx", "check_list_texto_dois.docx")


def find_template(explicit: Path | None = None) -> Path | None:
    """Procura o modelo do Checklist: caminho explícito, resources/, pasta do projeto ou pasta atual."""
    if explicit:
        return Path(explicit) if Path(explicit).is_file() else None
    here = Path(__file__).resolve().parent
    for base in (here.parent / "resources", here / "resources", here.parent, here, Path.cwd() / "resources", Path.cwd()):
        for name in TEMPLATE_NAMES:
            if (base / name).is_file():
                return base / name
    return None


def run_pipeline(manuscript: Path, out_dir: Path, cover: Path | None = None, attachments: Path | None = None,
                 template: Path | None = None, use_llm: bool = True, model: str = DEFAULT_MODEL, spelling: bool = True,
                 manuscript_id: str = "", names: dict | None = None, progress=lambda msg, pct: None, echo=None) -> dict:
    """`names` permite escolher os nomes dos arquivos gerados: {"json":..., "comentado":..., "checklist":...}."""
    names = {"json": "resultado.json", "comentado": "comentado.docx", "checklist": "checklist.docx", **(names or {})}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {"files": {}, "warnings": [], "ia": {"usada": False, "erro": None, "consultas": 0}}

    progress("Lendo o documento Word", 5)
    doc = load_document(manuscript)
    cov = load_document(cover) if cover else None
    ctx = Ctx(doc, cov, attachments, use_llm, model)

    progress("Verificando as regras do Checklist", 15)
    cat, sections = run_all(ctx)

    if use_llm:
        progress("Revisão por IA (pode levar alguns minutos)", 35)
        try:
            ai_review.apply(ctx, cat, sections, spell=spelling)
        except Exception as e:  # noqa: BLE001
            ctx.cache["ai_error"] = f"{type(e).__name__}: {e}"
        result["ia"] = {"usada": not ctx.cache.get("ai_error"), "erro": ctx.cache.get("ai_error"), "consultas": ctx.cache.get("ai_calls", 0)}
        if ctx.cache.get("ai_error"):
            result["warnings"].append(f"IA indisponível ({ctx.cache['ai_error']}): os itens de julgamento ficaram como 'verificar manualmente'.")

    progress("Aplicando verificações por código aos itens de julgamento", 80)
    heuristics.apply(ctx, cat, sections)         # sem IA (ou se a IA falhar): indícios objetivos em vez de "verificar manualmente"

    progress("Gerando os arquivos", 85)
    if echo:
        echo(cat, sections, ctx)
    from titles import title_lines
    tl = title_lines(ctx)
    title = tl[0].text if tl else ""
    meta = {"arquivo": doc.path.name, "gerado em": datetime.now().strftime("%d/%m/%Y %H:%M")}

    p_json = out_dir / names["json"]
    export_json(ctx, cat, sections, p_json, meta)
    result["files"]["json"] = p_json

    p_com = out_dir / names["comentado"]
    result["comentarios"] = write_commented(ctx, sections, cat, p_com)
    result["files"]["comentado"] = p_com

    tpl = find_template(template)
    if tpl is None:
        result["warnings"].append("Modelo do Checklist não encontrado (resources/Checklist_modelo.docx): o Checklist em Word não foi gerado.")
    else:
        p_chk = out_dir / names["checklist"]
        result["warnings"] += fill_checklist(ctx, cat, sections, tpl, p_chk, title, manuscript_id)
        result["files"]["checklist"] = p_chk

    c = summary(cat, sections)
    result["resumo"] = {k: c.get(k, 0) for k in ("A", "AP", "NA", "NSA", "-")}
    result["titulo"] = title
    progress("Concluído", 100)
    return result
