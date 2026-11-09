import re

from common import Ctx, note, res


def item_co_incorporada(ctx: Ctx):
    desc = "Não leva à conclusão em seção separada, sendo incorporada ao último parágrafo da discussão. A conclusão deve responder aos objetivos do estudo."
    S = ctx.sections
    if S.has("CONCLUSION"):
        h = S.heading["CONCLUSION"]
        return res("co.incorporada", desc, "NA",
                   f"Existe seção separada “{h.stripped}” ({ctx.where(h)}): em artigos originais a conclusão deve ser incorporada ao último parágrafo da Discussão. Remover a seção.",
                   [note(h, "Remova esta seção: a conclusão deve ser incorporada ao último parágrafo da Discussão e responder aos objetivos do estudo.")])
    D = S.get("DISCUSSION")
    if not D:
        return res("co.incorporada", desc, "-", "Discussão não encontrada")
    if not re.search(r"conclu|em\s+s[ií]ntese|em\s+suma|portanto|em\s+resumo", D[-1].text, re.IGNORECASE):
        return res("co.incorporada", desc, "AP", f"Sem seção de Conclusão, mas o último parágrafo da Discussão ({ctx.where(D[-1])}) não parece conter a conclusão",
                   [note(D[-1], "Incorpore aqui a conclusão, respondendo aos objetivos do estudo.")])
    return res("co.incorporada", desc, "A", "Conclusão incorporada ao último parágrafo da Discussão (adequação aos objetivos deve ser conferida manualmente)")
