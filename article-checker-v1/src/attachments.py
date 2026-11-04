"""DOCUMENTOS OBRIGATÓRIOS — verificação por nome de arquivo (opção --anexos PASTA)."""
import re
from pathlib import Path

from common import Ctx, res

REQUIRED = [
    (101, "Cópia do Parecer do Comitê de Ética em Pesquisa (CEP), com nº de protocolo e data de aprovação", r"parecer|cep|[eé]tica|conep"),
    (102, "Declaração de Originalidade", r"originalidade"),
    (103, "Declaração de Responsabilidade e de Transferência de Direitos Autorais preenchida e assinada", r"responsabilidade|direitos|autoral|transfer"),
    (104, "Termo de Compromisso de Tradução", r"tradu[cç]"),
    (105, "Arquivo com sugestão de avaliadores para o manuscrito", r"avaliador|revisor|indica[cç]"),
]


def _check(ctx: Ctx, item, desc, rx):
    d = ctx.attachments_dir
    if not d:
        return res(item, desc, "-", "Documento separado: informe a pasta com --anexos para verificar a presença do arquivo")
    files = [f.name for f in Path(d).iterdir() if f.is_file()]
    hit = [f for f in files if re.search(rx, f, re.IGNORECASE)]
    if hit:
        return res(item, desc, "A", f"Arquivo encontrado: {hit[0]} (conteúdo/assinaturas devem ser conferidos manualmente)")
    return res(item, desc, "NA", "Arquivo não encontrado na pasta de anexos")


def make(item, desc, rx):
    return lambda ctx: _check(ctx, item, desc, rx)


def item_106(ctx: Ctx):
    desc = "Folha de rosto (padrão RECI)"
    return res(106, desc, "A" if ctx.cover else "NA", "Folha de rosto enviada" if ctx.cover else "Folha de rosto não enviada")
