import sys
from pathlib import Path

from cli import init
from pipeline import run_pipeline
from render import render_result


def main():
    args = init()
    stem = args.manuscrito.stem
    r = run_pipeline(
        args.manuscrito, args.saida, cover=args.folha_de_rosto, attachments=args.anexos,
        template=args.modelo_checklist, use_llm=not args.sem_llm, model=args.modelo, spelling=not args.sem_ortografia,
        manuscript_id=args.id,
        names={"json": f"{stem}_checklist.json", "comentado": f"{stem}_comentado.docx", "checklist": f"{stem}_checklist.docx"},
        progress=lambda msg, pct: print(f"[{pct:3d}%] {msg}"),
        echo=lambda cat, sections, ctx: render_result(cat, sections),
    )
    for w in r["warnings"]:
        print("[aviso]", w)
    print(f"\nArquivos gerados em {args.saida.resolve()}:")
    for k, p in r["files"].items():
        print("  -", p.name)
    if r["resumo"]:
        print("Resumo:", r["resumo"])


if __name__ == "__main__":
    sys.exit(main())
