import argparse
import logging
import sys
from pathlib import Path

from common import DEFAULT_MODEL

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("reci-checker")


def _check_docx(path: Path, what: str):
    if not path.is_file():
        logger.error("%s não encontrado(a): %s", what, path)
        sys.exit(2)
    if path.suffix.lower() != ".docx":
        logger.error("Formato inválido (%s) para %s: a RECI aceita somente Word (.docx).", path.suffix, what)
        sys.exit(3)


def init():
    ap = argparse.ArgumentParser(description="Verifica a conformidade de manuscritos (.docx) com o Checklist da RECI.")
    ap.add_argument("manuscrito", type=Path, help="Manuscrito (.docx)")
    ap.add_argument("folha_de_rosto", type=Path, nargs="?", help="Folha de rosto (.docx) — opcional")
    ap.add_argument("--anexos", type=Path, help="Pasta com os documentos obrigatórios (parecer CEP, declarações...)")
    ap.add_argument("--saida", type=Path, default=Path("relatorios"), help="Pasta de saída (padrão: ./relatorios)")
    ap.add_argument("--id", default="", help="Nº de identificação do manuscrito (cabeçalho do Checklist)")
    ap.add_argument("--modelo-checklist", type=Path, default=None, help="Modelo do Checklist .docx (padrão: resources/Checklist_modelo.docx)")
    ap.add_argument("--sem-llm", action="store_true", help="Não usar IA (Ollama): itens de julgamento ficam como 'verificar manualmente'")
    ap.add_argument("--sem-ortografia", action="store_true", help="Não rodar a revisão ortográfica por IA (mais rápido)")
    ap.add_argument("--modelo", default=DEFAULT_MODEL, help=f"Modelo do Ollama (padrão: {DEFAULT_MODEL})")
    args = ap.parse_args()
    _check_docx(args.manuscrito, "Manuscrito")
    if args.folha_de_rosto:
        _check_docx(args.folha_de_rosto, "Folha de rosto")
    if args.anexos and not args.anexos.is_dir():
        logger.error("Pasta de anexos não encontrada: %s", args.anexos)
        sys.exit(2)
    return args
