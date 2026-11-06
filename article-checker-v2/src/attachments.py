"""DOCUMENTOS OBRIGATÓRIOS — verificação por nome de arquivo (opção --anexos PASTA).
Os links "Clique aqui para baixar: ..." do modelo do Checklist são preservados no Word gerado."""
import re
from pathlib import Path

from common import Ctx, res

REQUIRED = [
    ("doc.cep", "Cópia do Parecer do Comitê de Ética em Pesquisa (CEP), registrado na CONEP, com nº de protocolo e a data de aprovação", r"parecer|cep|[eé]tica|conep"),
    ("doc.originalidade", "Declaração de Originalidade", r"originalidade"),
    ("doc.responsabilidade", "Declaração de Responsabilidade e de Transferência de Direitos Autorais", r"responsabilidade|direitos|autoral|transfer"),
    ("doc.traducao", "Termo de Compromisso de Tradução", r"tradu[cç]"),
    ("doc.avaliadores", "Arquivo com sugestão de avaliadores para o manuscrito", r"avaliador|revisor|indica[cç]"),
]


def _check(ctx: Ctx, item, desc, rx):
    if item == "doc.cep":
        from body_sections import waived
        if waived(ctx):
            return res(item, desc, "NSA", "O manuscrito declara dispensa de apreciação ética/parecer do CEP (Métodos): documento não exigido.")
    d = ctx.attachments_dir
    if not d:
        return res(item, desc, "-", "Documento separado: informe a pasta com --anexos para verificar a presença do arquivo")
    files = [f.name for f in Path(d).iterdir() if f.is_file()]
    hit = [f for f in files if re.search(rx, f, re.IGNORECASE)]
    if hit:
        return res(item, desc, "A", f"Arquivo encontrado: {hit[0]} (conteúdo/assinaturas devem ser conferidos manualmente)")
    return res(item, desc, "NA", "Arquivo não encontrado na pasta de anexos: envie este documento junto ao manuscrito")


def make(item, desc, rx):
    return lambda ctx: _check(ctx, item, desc, rx)


def item_folha(ctx: Ctx):
    desc = "Folha de rosto (padrão RECI)"
    return res("doc.folha", desc, "A" if ctx.cover else "NA", "Folha de rosto enviada" if ctx.cover else "Folha de rosto não enviada")
