import argparse
import logging
import sys
from pathlib import Path

from common import DEFAULT_MODEL

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("reci-checker")
EXT = {".docx", ".pdf"}


def _check_file(path: Path, what: str, allowed=EXT):
    if not path.is_file():
        logger.error("%s não encontrado(a): %s", what, path)
        sys.exit(2)
    if path.suffix.lower() not in allowed:
        logger.error("Formato inválido (%s) para %s. Use: %s", path.suffix, what, ", ".join(sorted(allowed)))
        sys.exit(3)


def init():
    ap = argparse.ArgumentParser(description="Verifica a conformidade de manuscritos com o Checklist da RECI (.docx ou .pdf).")
    ap.add_argument("manuscrito", type=Path, help="Manuscrito (.docx ou .pdf)")
    ap.add_argument("folha_de_rosto", type=Path, nargs="?", help="Folha de rosto (.docx ou .pdf) — opcional")
    ap.add_argument("--anexos", type=Path, help="Pasta com os documentos obrigatórios (parecer CEP, declarações...)")
    ap.add_argument("--saida", type=Path, default=Path("relatorios"), help="Pasta dos relatórios (padrão: ./relatorios)")
    ap.add_argument("--sem-llm", action="store_true", help="Não usar o Ollama nos itens de Métodos (36–42)")
    ap.add_argument("--modelo", default=DEFAULT_MODEL, help=f"Modelo do Ollama (padrão: {DEFAULT_MODEL})")
    ap.add_argument("--sem-pdf", action="store_true", help="Não gerar o relatório em PDF")
    args = ap.parse_args()
    _check_file(args.manuscrito, "Manuscrito")
    if args.folha_de_rosto:
        _check_file(args.folha_de_rosto, "Folha de rosto")
    if args.anexos and not args.anexos.is_dir():
        logger.error("Pasta de anexos não encontrada: %s", args.anexos)
        sys.exit(2)
    return args
