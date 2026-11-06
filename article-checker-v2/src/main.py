import sys
from datetime import datetime
from pathlib import Path

from annotate import write_commented
from checklist import MANUAL, run_all
from checklist_docx import fill_checklist
from cli import init
from common import Ctx
from document_model import load_document
from render import export_json, render_result


def main():
    args = init()
    doc = load_document(args.manuscrito)
    cover = load_document(args.folha_de_rosto) if args.folha_de_rosto else None
    ctx = Ctx(doc, cover, args.anexos, not args.sem_llm, args.modelo)

    cat, sections = run_all(ctx)
    render_result(cat, sections)
    print("\nVerificação manual: " + "; ".join(MANUAL))

    out = args.saida
    out.mkdir(parents=True, exist_ok=True)
    stem = doc.path.stem
    from titles import title_lines
    tl = title_lines(ctx)
    title = tl[0].text if tl else ""
    tpl = args.modelo_checklist or Path(__file__).resolve().parent.parent / "resources" / "Checklist_modelo.docx"

    meta = {"arquivo": doc.path.name, "gerado em": datetime.now().strftime("%d/%m/%Y %H:%M")}
    export_json(ctx, cat, sections, out / f"{stem}_checklist.json", meta)
    for w in fill_checklist(ctx, cat, sections, tpl, out / f"{stem}_checklist.docx", title, args.id):
        print("[aviso]", w)
    n = write_commented(ctx, sections, cat, out / f"{stem}_comentado.docx")
    print(f"\nArquivos em {out.resolve()}:\n  {stem}_checklist.docx\n  {stem}_checklist.json\n  {stem}_comentado.docx ({n} comentários)")


if __name__ == "__main__":
    sys.exit(main())
