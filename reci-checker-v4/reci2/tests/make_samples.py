"""Gera manuscrito e folha de rosto de exemplo (com defeitos propositais) para testar o reci-checker."""
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH as AL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from PIL import Image

out = Path(sys.argv[1] if len(sys.argv) > 1 else "samples"); out.mkdir(exist_ok=True)
d = Document()
st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(12)
st.paragraph_format.line_spacing = 1.5; st.paragraph_format.space_after = Pt(0)


def para(text="", bold=False, italic=False, align=None, size=None, spacing=None, indent=None):
    p = d.add_paragraph()
    if text:
        r = p.add_run(text); r.bold = bold; r.italic = italic
        if size: r.font.size = Pt(size)
    if align is not None: p.alignment = align
    if spacing: p.paragraph_format.line_spacing = spacing
    if indent is not None: p.paragraph_format.first_line_indent = Cm(indent)
    return p


def body(text, indent=1.5, cites=None):
    p = para(text, indent=indent, align=AL.JUSTIFY)
    if cites:
        r = p.add_run(cites); r.font.superscript = True
    return p


def rich(parts, spacing=1.0, align=AL.JUSTIFY):
    p = d.add_paragraph()
    for t, b, i in parts:
        r = p.add_run(t); r.bold = b; r.italic = i
    p.paragraph_format.line_spacing = spacing; p.alignment = align
    return p


para("ARTIGO ORIGINAL", bold=True, align=AL.CENTER)
para("Mortalidade por doenças cardiovasculares em idosos no Brasil", bold=True, align=AL.CENTER, spacing=1.0)
para("Cardiovascular disease mortality among older adults in Brazil", italic=True, align=AL.CENTER, spacing=1.5)
para("Mortalidad por enfermedades cardiovasculares en ancianos en Brasil", italic=True, align=AL.CENTER, spacing=1.0)
for key, labs, txt, dl, desc, it in [
    ("RESUMO", ["Justificativa e Objetivos: ", "Métodos: ", "Resultados: ", "Conclusão: "],
     ["Analisar a mortalidade cardiovascular em idosos brasileiros. ", "Estudo ecológico com dados do SIM. ", "Houve queda das taxas. ", "A mortalidade diminuiu."], "Descritores", "Mortalidade; Doenças cardiovasculares; Idoso", False),
    ("ABSTRACT", ["Background and Objectives: ", "Methods: ", "Results: ", "Conclusion: "],
     ["To analyze cardiovascular mortality in older Brazilians. ", "Ecological study with SIM data. ", "Rates declined (Silva et al., 2019). ", "Mortality decreased."], "Keywords", "Mortality. Cardiovascular diseases. Aged. Brazil", True),
    ("RESUMEN", ["Justificación y Objetivos: ", "Métodos: ", "Resultados: ", "Conclusión: "],
     ["Analizar la mortalidad cardiovascular en ancianos brasileños. ", "Estudio ecológico con datos del SIM. ", "Las tasas disminuyeron. ", "La mortalidad disminuyó."], "Palabras Clave", "Mortalidad. Enfermedades cardiovasculares. Anciano. Brasil", True)]:
    para(key, bold=True, spacing=1.5)
    rich([x for l, t in zip(labs, txt) for x in ((l, True, False), (t, False, False))])
    rich([(dl + ": ", True, False), (desc, False, it)])
para("INTRODUÇÃO", bold=True)
body("As doenças cardiovasculares são a principal causa de morte no mundo. A mortalidade por HIV e por Covid-19 também cresceu. A Organização Mundial da Saúde (OMS) alerta para o problema. O SINAN registra agravos.", cites="1,2")
body("Segundo Silva et al. a mortalidade caiu em idosos.")
p = body("O objetivo deste estudo foi analisar a mortalidade cardiovascular em idosos brasileiros. ", indent=0)
para("MÉTODOS", bold=True)
body("Estudo ecológico de série temporal, realizado no Brasil, com a população idosa (60 anos ou mais). Foram incluídos todos os óbitos registrados no SIM. Os dados foram obtidos no DATASUS referentes ao período de 2010 a 2020. A análise utilizou cálculo de taxas. Foram observadas Escherichia coli em exames.")
body("A pesquisa seguiu a Resolução 510/2016. Parecer do CEP nº 4.123.456, aprovado em 12/05/2020. Este estudo foi dispensado do número do CAAE por utilizar dados públicos.")
para("RESULTADOS", bold=True)
body("A taxa caiu ao longo do período, como mostra a Tabela 1. Veja também a Figura 1 (Figura 1).")
cap = para("Tabela 1. Taxas de mortalidade cardiovascular em idosos, Brasil, 2010-2020", size=10, spacing=1.0)
t = d.add_table(rows=4, cols=3)
for i, row in enumerate([("Ano", "N", "%"), ("2010", "100", "50%"), ("2020", "80", "40%"), ("Total", "180", "90%")]):
    for j, v in enumerate(row):
        t.cell(i, j).text = v
para("")
Image.new("RGB", (200, 120), (200, 50, 50)).save(out / "fig.png", dpi=(72, 72))
pf = d.add_paragraph(); pf.add_run().add_picture(str(out / "fig.png"), width=Cm(10))
para("Figura 1. Série temporal", size=12, spacing=1.5)
para("DISCUSSÃO", bold=True)
body("Os achados concordam com a literatura.", cites="6,7,8")
body("Entre as limitações, destaca-se o uso de dados secundários.", cites="9")
body("Conclui-se que a mortalidade diminuiu.", cites="10")
para("CONCLUSÃO", bold=True)
body("A mortalidade caiu.")
para("REFERÊNCIAS", bold=True)
refs = [
 "Almeida MF, Facchini LA, Portela LE. Editorial. Rev Bras Epidemiol. 2012;15(4):691-3. http://dx.doi.org/10.1590/S1415-790X2012000400001.",
 "Malta DC, Morais Neto OL, Silva Junior JB. Apresentação do plano de ações estratégicas. Epidemiol Serv Saude. 2011;20(4):93-107. Disponível em: http://scielo.iec.pa.gov.br/pdf/ess/v20n4/v20n4a02.pdf.",
 "Calman JW, Josh MKH, Gehardt JE, Smith AB, Jones CD, Lee EF, Kim GH. Cardiovascular trends. Lancet. 2022;399(1):1-10. https://doi.org/10.1016/S0140-6736(22)00001-1.",
 "Posma DM, Bill D, Parker RJ, et al. Heart disease burden. N Engl J Med. 2021;384(2):100-9. https://doi.org/10.1056/NEJMx2100001.",
 "Silva J. B., Souza M. Mortalidade cardiovascular. Cad Saude Publica. 2020;36(5):e1-10. https://doi.org/10.1590/0102-311X00001.",
 "Lima CR, Pinto AP, Costa FG. Tendência da mortalidade por doenças cardiovasculares. Rev Saude Publica. 2019;53:10. https://doi.org/10.11606/s1518-8787.2019053001.",
 "Rojas AB, Garcia LM, Perez JK. Mortalidad cardiovascular en América Latina. Rev Panam Salud Publica. 2021;45:e12. https://doi.org/10.26633/RPSP.2021.12.",
 "Brown AB, Green CD, White EF. Aging and cardiovascular risk. Circulation. 2023;147(3):200-12. https://doi.org/10.1161/CIRC.0000000000001.",
 "Oliveira PQ, Santos RS, Almeida TU. Idosos e hipertensão no Brasil. Cienc Saude Colet. 2022;27(4):1-9. https://doi.org/10.1590/1413-81232022274.",
 "Ministério da Saúde. Painel de monitoramento da mortalidade. Brasília: MS; 2020. https://www.gov.br/saude.",
]
for i, r in enumerate(refs, 1):
    para(f"{i}. {r}", spacing=1.5, align=AL.LEFT)
d.core_properties.author = "Fulano de Tal"
d.save(out / "manuscrito.docx")

c = Document()
for ln in ["Título: Mortalidade por doenças cardiovasculares em idosos no Brasil",
           "Autor: Maria Souza Lima1", "ORCID: https://orcid.org/0000-0002-1825-0097", "Currículo lattes: http://lattes.cnpq.br/1234567890123456",
           "Afiliação: Universidade Federal do Rio Grande do Sul, Porto Alegre, Rio Grande do Sul, Brasil.",
           "Resumo da Biografia: Enfermeira, Doutora em Epidemiologia.", "Instagram: @maria.lima",
           "Autor Correspondente: Maria Souza Lima", "E-mail: maria@ufrgs.br"]:
    c.add_paragraph(ln)
p = c.add_paragraph(); p.add_run("Contribuições dos autores:")
p = c.add_paragraph(); r = p.add_run("Maria Souza Lima "); r.bold = True; p.add_run("concepção e análise dos dados.")
c.save(out / "folha_de_rosto.docx")
