"""Catálogo dos itens do Checklist RECI (modelo check_list_texto_dois.docx) + alterações da revista.

Os ids são estáveis; `text` é o texto ORIGINAL da linha do modelo (usado para conferir o casamento com o Word).
`OVERRIDES` lista as alterações pedidas pela RECI em relação ao modelo (aplicadas no Word gerado).
"""
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Item:
    id: str
    section: str
    text: str


CATALOG: list[Item] = [
    Item('plag.plagio', 'DETECÇÃO DE PLÁGIO', 'Detecção de plágio ≤ 35%'),
    Item('doc.cep', 'DOCUMENTOS OBRIGATÓRIOS', 'Cópia do Parecer do Comitê de Ética em Pesquisa (CEP), registrado na CONEP, com nº de protocolo e a data de aprovação'),
    Item('doc.originalidade', 'DOCUMENTOS OBRIGATÓRIOS', 'Declaração de Originalidade'),
    Item('doc.responsabilidade', 'DOCUMENTOS OBRIGATÓRIOS', 'Declaração de Responsabilidade e de Transferência de Direitos Autorais com todos os dados preenchidos de forma correta (título, local, data, nomes completos dos autores, contribuições de autoria e assinaturas)'),
    Item('doc.traducao', 'DOCUMENTOS OBRIGATÓRIOS', 'Termo de Compromisso de Tradução'),
    Item('doc.avaliadores', 'DOCUMENTOS OBRIGATÓRIOS', 'Arquivo com sugestão de avaliadores para o manuscrito'),
    Item('doc.folha', 'DOCUMENTOS OBRIGATÓRIOS', 'Folha de rosto'),
    Item('fr.titulo', 'FOLHA DE ROSTO', 'Apresenta título do artigo'),
    Item('fr.autores', 'FOLHA DE ROSTO', 'A autoria é composta de, no máximo, 10 autores (exceção em multicêntricos)'),
    Item('fr.nomes', 'FOLHA DE ROSTO', 'Nome completo dos autores, sem abreviações'),
    Item('fr.afiliacao', 'FOLHA DE ROSTO', 'Instituição/Afiliação (com cidade e UF)'),
    Item('fr.links', 'FOLHA DE ROSTO', 'Link ORCID e lattes'),
    Item('fr.email', 'FOLHA DE ROSTO', 'E-mail e endereço do autor correspondente'),
    Item('fr.biografia', 'FOLHA DE ROSTO', 'Resumo da Biografia (categoria profissional e maior titulação).'),
    Item('fr.redes', 'FOLHA DE ROSTO', 'Rede social de todos os autores (preferencialmente Instagram) para futura divulgação do artigo'),
    Item('fr.contribuicoes', 'FOLHA DE ROSTO', 'São especificadas quais foram as contribuições individuais de cada autor na elaboração do artigo, no seguinte formato: nome completo de cada autor (em negrito e escrito por extenso), seguido das contribuições:\nEx.: Marília Saraiva concepção análise e interpretação de dados.'),
    Item('fg.autoria', 'FORMATAÇÃO GERAL DO MANUSCRITO', 'A identificação de autoria do trabalho foi removida do arquivo e da opção Propriedades no Word'),
    Item('fg.formato', 'FORMATAÇÃO GERAL DO MANUSCRITO', 'Está em formato Microsoft Word, digitado em .doc, até 2MB'),
    Item('fg.fonte', 'FORMATAÇÃO GERAL DO MANUSCRITO', 'Redigido na ortografia oficial, fonte Times New Roman 12, com espaçamento 1,5, sem espaçamento entre parágrafos'),
    Item('fg.simples', 'FORMATAÇÃO GERAL DO MANUSCRITO', 'Títulos do manuscrito, Resumos, Figuras, Tabelas e Referências devem estar com espaçamento simples.'),
    Item('fg.italico', 'FORMATAÇÃO GERAL DO MANUSCRITO', 'Itálico para palavras de idioma diferente do manuscrito\nEx.: nomes científicos: Acinetobacter baumanii, Klebsiella pneumoniae), softwares.'),
    Item('fg.secoes', 'FORMATAÇÃO GERAL DO MANUSCRITO', 'Deve ser dividido nas seguintes seções:\nINTRODUÇÃO\nMÉTODOS\nRESULTADOS\nDISCUSSÃO\nAGRADECIMENTOS (opcional)\nREFERÊNCIAS'),
    Item('fg.esquerda', 'FORMATAÇÃO GERAL DO MANUSCRITO', 'Todos os títulos estão alinhados à margem esquerda.'),
    Item('fg.espac_secoes', 'FORMATAÇÃO GERAL DO MANUSCRITO', 'Todos os títulos das seções estão com espaçamento 1,5.'),
    Item('fg.recuo', 'FORMATAÇÃO GERAL DO MANUSCRITO', 'Todos os parágrafos devem estar com recuo de 1,5.'),
    Item('fg.palavras', 'FORMATAÇÃO GERAL DO MANUSCRITO', 'Apresenta no máximo 4.000 palavras (da Introdução à Discussão)'),
    Item('ti.max15', 'TÍTULO DO MANUSCRITO', 'Inédito, curto, claro e conciso, identifica o conteúdo do manuscrito, com no máximo 15 palavras'),
    Item('ti.idiomas', 'TÍTULO DO MANUSCRITO', 'Títulos nos três idiomas (português, inglês e espanhol), um abaixo do outro'),
    Item('ti.principal', 'TÍTULO DO MANUSCRITO', 'Título principal em negrito, centralizado, fonte tamanho 12, espaçamento simples e apenas a primeira letra em maiúsculo.'),
    Item('ti.idioma_trabalho', 'TÍTULO DO MANUSCRITO', 'O primeiro título apresentado deve ser do mesmo idioma do trabalho.'),
    Item('ti.secundarios', 'TÍTULO DO MANUSCRITO', 'Títulos secundários nos diferentes idiomas devem estar em itálico, centralizado, fonte tamanho 12, espaçamento simples e apenas a primeira letra em maiúsculo'),
    Item('ti.plataforma', 'TÍTULO DO MANUSCRITO', 'O título do manuscrito foi cadastrado em inglês na plataforma, com apenas a primeira letra em maiúsculo (Equipe RECI olhar no sistema - Publicação → títulos)'),
    Item('re.abaixo', 'RESUMOS', 'Abaixo dos títulos, com versões nos três idiomas'),
    Item('re.conciso', 'RESUMOS', 'Conciso, limite máximo de 250 palavras, em parágrafo único, com espaçamento simples entre as linhas'),
    Item('re.resumo', 'RESUMOS', 'RESUMO - Justificativa e Objetivos, Métodos, Resultados e Conclusão (versão portuguesa)\nTodos em negrito e seguido por dois pontos.'),
    Item('re.abstract', 'RESUMOS', 'ABSTRACT - Background and Objectives, Methods, Results e Conclusion (versão inglesa)\nTodos em negrito e seguido por dois pontos.'),
    Item('re.resumen', 'RESUMOS', 'RESUMEN - Justificación y Objetivos, Métodos, Resultados e Conclusión (versão espanhola).\nTodos em negrito e seguido por dois pontos.'),
    Item('re.autores', 'RESUMOS', 'Não deve haver citação de autores nos resumos.'),
    Item('de.abaixo', 'DESCRITORES', 'Apresentados abaixo de cada versão do resumo, citados nos idiomas português, inglês e espanhol.'),
    Item('de.quantidade', 'DESCRITORES', 'Apresenta de 3 a 5 descritores, segundo o Descritores em Ciências da Saúde da Bireme (DeCS) disponível em: https://decs.bvsalud.org.'),
    Item('de.termos', 'DESCRITORES', 'Utiliza as terminologias\nPortuguês: “Descritores”\nInglês: “Keywords”\nEspanhol: “Palabras Clave”\nTodos em negrito e a primeira letra maiúscula alinhados à esquerda da margem'),
    Item('de.italico', 'DESCRITORES', 'Descritores, Keywords e Palabras Clave apresentam-se grifadas em itálico, separadas por ponto final e com a primeira letra de cada palavra em caixa alta.\nEx.: Descritores: HIV. Covid-19. Isolamento social. Adesão à medicação. Antirretrovirais.'),
    Item('in.breve', 'INTRODUÇÃO', 'Breve, apresenta a revisão da literatura, justificativa e objetivo.'),
    Item('in.objetivo', 'INTRODUÇÃO', 'O objetivo é coerente com a proposta do estudo, idêntico ao apresentado no resumo, destacado no último parágrafo da introdução e é iniciado por verbo no infinitivo.'),
    Item('in.autores', 'INTRODUÇÃO', 'Não apresenta citações com os nomes de autores em destaque no texto.'),
    Item('me.delineamento', 'MÉTODO', 'Delineamento/período de realização do estudo'),
    Item('me.cenario', 'MÉTODO', 'Cenário estudado'),
    Item('me.populacao', 'MÉTODO', 'População'),
    Item('me.criterios', 'MÉTODO', 'Critérios de seleção (inclusão/exclusão)'),
    Item('me.fonte', 'MÉTODO', 'Fonte de dados'),
    Item('me.periodo', 'MÉTODO', 'Período de coleta dos dados'),
    Item('me.analise', 'MÉTODO', 'Tipo de análise realizada'),
    Item('me.etica', 'MÉTODO', 'Considerações éticas devem estar descritas no último parágrafo da seção de métodos'),
    Item('me.objetiva', 'MÉTODO', 'As informações devem ser descritas de forma objetiva e completa'),
    Item('me.autores', 'MÉTODO', 'Não apresenta citações com os nomes de autores em destaque no texto.'),
    Item('et.parecer', 'ASPECTOS ÉTICOS', 'Para estudos que envolvem\xa0seres humanos, indica no último parágrafo do método o parecer CEP'),
    Item('et.resolucoes', 'ASPECTOS ÉTICOS', 'Apresenta que a pesquisa foi conduzida de acordo com os padrões éticos exigidos - Resoluções 466/2012 - 510/2016 - 580/2018, do Ministério da Saúde'),
    Item('et.protocolo', 'ASPECTOS ÉTICOS', 'Apresenta o número do protocolo de aprovação do projeto de pesquisa e data de aprovação do projeto de pesquisa no Comitê de Ética em Pesquisa'),
    Item('et.caae', 'ASPECTOS ÉTICOS', 'O número do CAAE (Certificado de Apresentação de Apreciação Ética) foi adicionado nos Métodos'),
    Item('rs.sequencia', 'RESULTADOS', 'Os resultados estão descritos em sequência lógica.'),
    Item('rs.ilustracoes', 'RESULTADOS', 'Apresenta tabelas e ilustrações em sequência lógica, com texto complementar a essas. (no máximo 5 ilustrações).'),
    Item('di.limitacoes', 'DISCUSSÃO', 'Indica no penúltimo parágrafo as limitações do estudo e formas de mitigação'),
    Item('di.literatura', 'DISCUSSÃO', 'Apresenta os resultados comparados com os resultados da literatura e adequadamente discutidos.'),
    Item('di.autores', 'DISCUSSÃO', 'Não apresenta citações com os nomes de autores em destaque no texto.'),
    Item('co.incorporada', 'CONCLUSÃO', 'Não leva à conclusão em seção separada, sendo incorporada ao último parágrafo da discussão. A conclusão deve responder aos objetivos do estudo.'),
    Item('si.siglas', 'SÍMBOLOS, ABREVIATURAS E SIGLAS', 'Siglas ou acrônimos com até três letras deverão ser escritos com maiúsculas (Ex: DOU; USP; OIT). Em sua primeira aparição no texto, serão escritos por extenso, acompanhados da sigla entre parênteses'),
    Item('si.termos', 'SÍMBOLOS, ABREVIATURAS E SIGLAS', 'Quando presentes, os seguintes termos devem estar descritos da seguinte maneira: Covid-19, HIV, Aids.'),
    Item('tb.max5', 'TABELAS', 'Apresenta no máximo 5 figuras e/ou tabelas que devem estar apresentadas no corpo do texto'),
    Item('tb.editaveis', 'TABELAS', 'Tabelas são editáveis? Estão numeradas em ordem sequencial? Transmitem os dados de forma clara?'),
    Item('tb.titulo', 'TABELAS', 'Tabelas estão tituladas em cima, alinhadas à esquerda, fonte no tamanho 10 e com espaçamentos simples'),
    Item('tb.citacao', 'TABELAS', 'As tabelas não devem ser citadas ao longo do texto, devendo ser mencionadas apenas no final do parágrafo entre parênteses.\nEx.: Texto……… (Tabela 1).'),
    Item('tb.linhas', 'TABELAS', 'Nas tabelas não há linhas entre as variáveis e nem linhas de fundo e o espaçamento entre as variáveis é simples'),
    Item('tb.word', 'TABELAS', 'Tabelas são elaboradas no Word'),
    Item('tb.n_pct', 'TABELAS', 'Tabelas com N e % na mesma coluna, não devendo aparecer de forma separada. O símbolo “% não deve aparecer nos dados da tabela.\nEx.: N (%)\n10 (100)'),
    Item('tb.siglas', 'TABELAS', 'As siglas devem ser escritas embaixo da tabela, com fonte tamanho 10 e espaçamento simples.'),
    Item('tb.total', 'TABELAS', 'Não deve haver uma linha com o total (somatório) dos dados.'),
    Item('tb.explicativo', 'TABELAS', 'Os títulos das tabelas e/ou figuras apresentam conteúdo explicativo, bem como informação sobre o recorte geográfico e temporal do estudo.\nEx.:\nTabela 1. Distribuição das características sociodemográficas e econômicas e qualidade de vida, entre pessoas com hipertensão arterial assistidas pela Estratégia Saúde da Família, Curitiba, Paraná, 2020.'),
    Item('fi.qualidade', 'FIGURAS (GRÁFICOS, MAPAS, etc.)', 'Figuras apresentam boa qualidade? Estão numeradas em ordem sequencial?'),
    Item('fi.titulo', 'FIGURAS (GRÁFICOS, MAPAS, etc.)', 'Figuras tituladas embaixo, alinhadas à esquerda, tamanho 10 e com espaçamento simples (exemplo: gráficos e mapas)'),
    Item('fi.centralizada', 'FIGURAS (GRÁFICOS, MAPAS, etc.)', 'A ilustração deve estar centralizada no texto.'),
    Item('fi.cor', 'FIGURAS (GRÁFICOS, MAPAS, etc.)', 'Gráficos estão padronizados preferencialmente em cores em tom azul.'),
    Item('fi.graf_titulo', 'FIGURAS (GRÁFICOS, MAPAS, etc.)', 'Gráficos estão titulados embaixo, alinhadas à esquerda, fonte no tamanho 10 e com espaçamentos simples'),
    Item('fi.citacao', 'FIGURAS (GRÁFICOS, MAPAS, etc.)', 'As figuras não devem ser citadas ao longo do texto, devendo ser mencionadas apenas no final do parágrafo entre parênteses.\nEx.: Texto……… (Figura 1).'),
    Item('fi.explicativo', 'FIGURAS (GRÁFICOS, MAPAS, etc.)', 'Os títulos das tabelas e/ou figuras apresentam conteúdo explicativo, bem como informação sobre o recorte geográfico e temporal do estudo.\nEx.:\nFigura 1. Série e tendência temporal das taxas de detecção de sífilis, Recife, Pernambuco, 2011 - 2021.'),
    Item('rt.citacoes', 'REFERÊNCIAS AO LONGO DO TEXTO', 'Estão dispostas no texto em\xa0ordem sequencial numérica, sendo obrigatória a sua citação, sobrescrita e sem parêntesis sempre no final do devido parágrafo após o ponto final. Separados entre si por vírgulas; em caso de números sequenciais de referências, separá-los por um hífen, enumerando apenas a primeira e a última referência do intervalo sequencial de citação (exemplo:\xa07,10-16)'),
    Item('rt.autores', 'REFERÊNCIAS AO LONGO DO TEXTO', 'Não apresenta citações com os nomes de autores em destaque no texto'),
    Item('rf.vancouver', 'REFERÊNCIAS', 'Apresentam-se nas Normas de Vancouver\nA RECI adota as “Normas de Vancouver”, disponível em http://www.icmje.org, como referência para a veiculação de seus trabalhos, para as abreviações de revistas buscar no Index Medicus/MedLine.'),
    Item('rf.formato', 'REFERÊNCIAS', 'Estão em fonte 12, espaçamento simples, justificado'),
    Item('rf.internacionais', 'REFERÊNCIAS', 'Apresenta, majoritariamente, 40% de referências internacionais nos últimos 5 anos'),
    Item('rf.recentes', 'REFERÊNCIAS', 'Utilizaram-se referências, majoritariamente, de manuscritos publicados nos últimos cinco anos, nacional e internacional'),
    Item('rf.doi', 'REFERÊNCIAS', 'Apresentam DOI nas referências ou endereço eletrônico?\nEx com DOI: Almeida MF, Facchini LA, Portela LE. EDITORIAL. Rev Bras Epidemiol 2012; 15 (4): 691 693.\xa0http://dx.doi.org/10.1590/S1415-790X2012000400001.\nEx sem DOI: Malta DC, Morais Neto OL, Silva Junior JB. Apresentação do plano de ações estratégicas para o enfrentamento das doenças crônicas não transmissíveis no Brasil, 2011 a 2022. Epidemiol Serv Saude 2011; 20 (4):93-107. http://scielo.iec.pa.gov.br/pdf/ess/v20n4/v20n4a02.pdf.\n*DOI ou endereço eletrônico devem estar em hiperlink'),
    Item('rf.autores', 'REFERÊNCIAS', 'Referencia-se o(s) autor(e)s pelo\xa0sobrenome. A letra inicial é maiúscula, seguida do(s) nome(s) abreviado(s) e sem o ponto. Ex: Posma DM, Bill D, Parker RJ'),
    Item('rf.etal', 'REFERÊNCIAS', 'Artigos com mais de 6 autores - citam o três primeiros nomes dos autores antes da expressão “et al”.\nEx: Calman JW, Josh MKH, Gehardt JE, et al.\nManuscrito no qual o nome do autor possui designação familiar, o grau de parentesco deve ser apresentado logo após o sobrenome.\nEx.: Morais Neto, Oliveira Júnior'),
]

BY_ID = {i.id: i for i in CATALOG}

CATEGORY_TEXT = "Mínimo de 10 e máximo de 25 referências no últimos 5 anos"

# Alterações em relação ao modelo: id -> lista de operações ("replace", antigo, novo) | ("append", texto) | ("append_par", texto)
OVERRIDES: dict[str, list[tuple]] = {
    "doc.cep": [("append", " (dispensável quando o manuscrito declara a dispensa de apreciação ética)")],
    "fg.secoes": [("append_par", "CONTRIBUIÇÃO DOS AUTORES (após as REFERÊNCIAS)")],
    "re.conciso": [("replace", "250", "256")],
    "et.parecer": [("append", " (exceto se o manuscrito declarar a dispensa)")],
    "et.protocolo": [("append", " (exceto se o manuscrito declarar a dispensa)")],
    "et.caae": [("append", " (exceto se o manuscrito declarar a dispensa)")],
    "rt.citacoes": [("replace", "no final do devido parágrafo após o ponto final", "no final da frase, após o ponto final")],
    "rf.vancouver": [("append_par", "Não utilizar “Disponível em:”, “Available from/at:” etc.: informar somente o link.")],
}

def display_text(item_id: str) -> str:
    """Texto da linha já com as alterações da RECI (para JSON/terminal)."""
    t = BY_ID[item_id].text
    for op in OVERRIDES.get(item_id, []):
        if op[0] == "replace":
            t = t.replace(op[1], op[2])
        elif op[0] == "append":
            t += op[1]
        else:
            t += "\n" + op[1]
    return t
