import re

from common import Ctx, res


def item_53(ctx: Ctx):
    desc = "Não leva conclusão em seção separada, sendo incorporada ao último parágrafo da discussão"
    S = ctx.sections
    if S.has("CONCLUSION"):
        return res(53, desc, "NA", "Existe seção separada de Conclusão/Considerações finais (artigos originais devem incorporá-la à Discussão)")
    D = S.get("DISCUSSION")
    if not D:
        return res(53, desc, "-", "Discussão não encontrada")
    if not re.search(r"conclu|em\s+s[ií]ntese|em\s+suma|portanto|em\s+resumo", D[-1].text, re.IGNORECASE):
        return res(53, desc, "AP", "Sem seção de Conclusão, mas o último parágrafo da Discussão não parece conter a conclusão")
    return res(53, desc, "A", "Conclusão incorporada ao último parágrafo da Discussão")
