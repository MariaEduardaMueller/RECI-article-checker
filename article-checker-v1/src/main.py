import sys
from datetime import datetime

from checklist import MANUAL, run_all
from cli import init
from common import Ctx
from document_model import load_document
from pdf_render import export_results_to_pdf
from render import export_json, render_result


def main():
    args = init()
    doc = load_document(args.manuscrito)
    cover = load_document(args.folha_de_rosto) if args.folha_de_rosto else None
    ctx = Ctx(doc, cover, args.anexos, not args.sem_llm, args.modelo)

    if not doc.exact:
        print("⚠ Manuscrito em PDF: fontes, negrito, itálico e sobrescrito são lidos com exatidão; alinhamento, "
              "espaçamento, parágrafos e tabelas são ESTIMADOS. Envie o .docx para a verificação completa.\n")

    sections = run_all(ctx)
    render_result(sections)
    print("\nVerificação manual: " + "; ".join(MANUAL))

    args.saida.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    meta = {"arquivo": doc.path.name, "formato": doc.fmt.upper(), "gerado em": datetime.now().strftime("%d/%m/%Y %H:%M")}
    export_json(sections, args.saida / f"relatorio_reci_checker_{stamp}.json", meta)
    if not args.sem_pdf:
        export_results_to_pdf(sections, args.saida / f"relatorio_reci_checker_{stamp}.pdf", MANUAL, meta)


if __name__ == "__main__":
    sys.exit(main())
