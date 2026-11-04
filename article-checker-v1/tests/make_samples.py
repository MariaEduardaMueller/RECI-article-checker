"""Gera manuscritos de teste (.docx) — um bem formatado e outro cheio de erros —
e a folha de rosto. Uso: python tests/make_samples.py <pasta_saida>"""
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH as AL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from PIL import Image, ImageDraw

LOREM = [
    "A mortalidade hospitalar entre idosos permanece como um desafio para os sistemas de saúde em todo o mundo, sobretudo em países de renda média.",
    "No Brasil, o envelhecimento acelerado da população amplia a demanda por leitos e exige o planejamento de ações específicas para esse grupo etário.",
    "Estudos prévios indicam que a fragilidade, a multimorbidade e o estado nutricional influenciam diretamente os desfechos clínicos observados.",
]


def set_cell_border(tbl, top=True, bottom=True, inner=False):
    tblPr = tbl._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        on = {"top": top, "bottom": bottom, "insideH": inner, "insideV": inner}.get(side, False)
        el.set(qn("w:val"), "single" if on else "nil")
        if on:
            el.set(qn("w:sz"), "4")
            el.set(qn("w:color"), "000000")
        borders.append(el)
    tblPr.append(borders)


def build(path: Path, bad: bool):
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Arial" if bad else "Times New Roman"
    st.font.size = Pt(12)
    st.paragraph_format.line_spacing = 1.0 if bad else 1.5
    st.paragraph_format.space_after = Pt(8 if bad else 0)
    st.paragraph_format.space_before = Pt(0)
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Inches(1.1)
    doc.core_properties.author = "Maria Souza Lima" if bad else ""
    doc.core_properties.last_modified_by = ""

    def P(text="", align=AL.JUSTIFY, bold=False, italic=False, size=None, spacing=None, after=None):
        p = doc.add_paragraph()
        p.alignment = align
        if spacing is not None:
            p.paragraph_format.line_spacing = spacing
        if after is not None:
            p.paragraph_format.space_after = Pt(after)
        if text:
            r = p.add_run(text)
            r.bold, r.italic = bold, italic
            if size:
                r.font.size = Pt(size)
        return p

    def with_cite(text, cite):
        p = P()
        p.add_run(text)
        if bad:
            p.add_run(f" ({cite})")
        else:
            r = p.add_run(cite)
            r.font.superscript = True
        return p

    def heading(t):
        P(t, align=AL.LEFT, bold=True)

    # ---- bloco de título/autores -------------------------------------------------
    P("ARTIGO ORIGINAL", align=AL.LEFT, bold=True)
    P("Fatores Associados à Mortalidade em Idosos Hospitalizados no Brasil" if bad else
      "Fatores associados à mortalidade em idosos hospitalizados no Brasil",
      align=AL.CENTER, bold=not bad, spacing=1.5 if bad else 1.0, after=0)
    for t in ("Factors associated with mortality in hospitalized older adults in Brazil",
              "Factores asociados a la mortalidad en ancianos hospitalizados en Brasil"):
        P(t, align=AL.CENTER, italic=not bad, bold=bad, spacing=1.0, after=0)
    for name, n, orcid in (("Maria Souza Lima", "1", "0000-0001-2345-6789"), ("João Pedro Alves", "2", "0000-0002-3456-7890")):
        p = P(name, align=AL.LEFT, spacing=1.0, after=0)
        r = p.add_run(n)
        r.font.superscript = True
        p.add_run(f" ORCID {orcid}")
    for n, aff in (("1", "Universidade Estadual de Ponta Grossa, Ponta Grossa, Paraná, Brasil."),
                   ("2", "Universidade Federal do Paraná, Curitiba, Paraná, Brasil.")):
        p = P(align=AL.LEFT, spacing=1.0, after=0)
        p.add_run(n).font.superscript = True
        p.add_run(aff)

    # ---- resumos -----------------------------------------------------------------
    def abstract(title, labels, texts, desc_label, descs):
        P(title, align=AL.LEFT, bold=True, spacing=1.0)
        p = P(spacing=1.0, after=0)
        for lab, tx in zip(labels, texts):
            r = p.add_run(lab + " ")
            r.bold = True
            p.add_run(tx + " ")
        d = P(align=AL.LEFT, spacing=1.0, after=0)
        d.add_run(desc_label + " ").bold = True
        d.add_run(descs).italic = not bad

    abstract("RESUMO", ["Justificativa e Objetivos:", "Métodos:", "Resultados:", "Conclusão:"],
             ["A mortalidade em idosos é elevada. Objetivou-se analisar fatores associados à mortalidade hospitalar.",
              "Estudo de coorte retrospectiva com dados do Sistema de Informações Hospitalares.",
              "Foram incluídos 1.200 idosos; a mortalidade foi de 14%.",
              "A fragilidade associou-se ao óbito."],
             "Descritores:", "HIV; Idoso; Mortalidade hospitalar; Fragilidade." if bad else "Idoso. Mortalidade hospitalar. Fragilidade. Saúde do idoso.")
    abstract("ABSTRACT", ["Background and Objectives:", "Methods:", "Results:", "Conclusion:"],
             ["Mortality is high. The aim was to analyze factors associated with in-hospital mortality.",
              "Retrospective cohort using the Hospital Information System.",
              "A total of 1,200 older adults were included; mortality was 14%.",
              "Frailty was associated with death."],
             "Keywords:", "Aged; Hospital mortality; Frailty." if bad else "Aged. Hospital mortality. Frailty. Health of the elderly.")
    abstract("RESUMEN", ["Justificación y Objetivos:", "Métodos:", "Resultados:", "Conclusión:"],
             ["La mortalidad es alta. El objetivo fue analizar factores asociados.",
              "Cohorte retrospectiva con datos del Sistema de Información Hospitalaria.",
              "Se incluyeron 1.200 ancianos; la mortalidad fue del 14%.",
              "La fragilidad se asoció con la muerte."],
             "Palabras Clave:", "Anciano; Mortalidad hospitalaria; Fragilidad." if bad else "Anciano. Mortalidad hospitalaria. Fragilidad. Salud del anciano.")

    # ---- introdução ----------------------------------------------------------------
    heading("INTRODUÇÃO")
    with_cite(LOREM[0], "1")
    with_cite(LOREM[1] + " Segundo Silva et al. (2020), o cenário é preocupante." if bad else LOREM[1], "2,3,4" if bad else "2-4")
    with_cite(LOREM[2] + (" A OMS destaca esse tema, sobretudo na UTI." if bad else " A Organização Mundial da Saúde (OMS) destaca esse tema."), "5")
    with_cite("O objetivo deste estudo foi analisar os fatores associados à mortalidade hospitalar em idosos." if not bad
              else "O presente estudo trata da mortalidade hospitalar em idosos brasileiros.", "6")

    # ---- métodos --------------------------------------------------------------------
    heading("MÉTODOS")
    with_cite("Trata-se de coorte retrospectiva realizada em hospitais públicos do Paraná, Brasil, entre janeiro de 2015 e dezembro de 2020.", "7")
    with_cite("A população foi composta por todos os idosos com 60 anos ou mais internados no Sistema Único de Saúde (SUS); os dados foram obtidos do Sistema de Informações Hospitalares. Utilizou-se regressão de Poisson.", "8")
    if bad:
        P("A pesquisa foi aprovada pelo Comitê de Ética em Pesquisa (CEP) sob o parecer nº 4.123.456 e CAAE 12345678.9.0000.0000.")
    else:
        P("O estudo seguiu as Resoluções 466/2012 e 510/2016 do Conselho Nacional de Saúde e foi aprovado pelo Comitê de Ética em Pesquisa (CEP), "
          "parecer nº 4.123.456, de 12/03/2020, CAAE 12345678.9.0000.0000.")

    # ---- resultados -----------------------------------------------------------------
    heading("RESULTADOS")
    with_cite("Foram incluídos 1.200 idosos, conforme a Tabela 1. A mortalidade foi de 14%, como mostra a Figura 1.", "9")
    cap = P("Tabela 1. Distribuição das características sociodemográficas de idosos hospitalizados, Paraná, Brasil, 2015-2020.",
            align=AL.CENTER if bad else AL.LEFT, size=12 if bad else 10, spacing=1.5 if bad else 1.0, after=0)
    t = doc.add_table(rows=3, cols=3)
    for i, row in enumerate((("Variável", "n", "%"), ("Sexo feminino", "700", "58,3"), ("Idade ≥ 80 anos", "300", "25,0"))):
        for j, v in enumerate(row):
            c = t.cell(i, j)
            c.text = v
            for pp in c.paragraphs:
                pp.paragraph_format.line_spacing = 1.5 if bad else 1.0
                pp.paragraph_format.space_after = Pt(0)
                for rr in pp.runs:
                    rr.font.size = Pt(10)
    set_cell_border(t, inner=bad)
    img_path = path.parent / "fig.png"
    im = Image.new("RGB", (1500, 900), "white")
    ImageDraw.Draw(im).line([(50, 800), (700, 300), (1400, 100)], fill="black", width=8)
    im.save(img_path)
    doc.add_picture(str(img_path), width=Inches(5))
    P("Figura 1. Série temporal da mortalidade hospitalar de idosos, Paraná, Brasil, 2015-2020." if not bad
      else "Figura 1. Série temporal.", align=AL.CENTER if bad else AL.LEFT, size=12 if bad else 10,
      spacing=1.0, after=0)
    if bad:
        for k in range(2, 6):
            P(f"Tabela {k}. Outra tabela.", align=AL.LEFT, size=10)
            tt = doc.add_table(rows=2, cols=2)
            tt.cell(0, 0).text = "a"
            tt.cell(1, 1).text = "b"
    with_cite("A fragilidade foi o principal fator associado ao óbito, com razão de risco de 2,1.", "10")

    # ---- discussão ------------------------------------------------------------------
    heading("DISCUSSÃO")
    with_cite("Os achados são consistentes com a literatura internacional, que aponta a fragilidade como preditor de mortalidade.", "11,12")
    with_cite("Observou-se mortalidade superior à relatada em estudos europeus, possivelmente pelo acesso tardio aos serviços.", "13-15")
    if bad:
        P("Entre as limitações do estudo, destaca-se o uso de dados secundários, cuja qualidade pode variar. Sugere-se mitigar esse viés com estudos futuros. Nesse sentido, os resultados devem ser interpretados com cautela.")
        P("Conclui-se que a fragilidade associa-se à mortalidade.")
        heading("CONCLUSÃO")
        P("A fragilidade deve ser avaliada na admissão.")
    else:
        P("Entre as limitações do estudo, destaca-se o uso de dados secundários, cuja qualidade pode variar; para mitigar esse viés, utilizaram-se procedimentos de validação e sugerem-se estudos futuros com dados primários.")
        P("Conclui-se que a fragilidade associa-se à mortalidade hospitalar e deve ser avaliada na admissão do idoso.")

    # ---- referências ----------------------------------------------------------------
    heading("REFERÊNCIAS")
    refs = [
        "Silva AB, Souza CD, Lima EF. Mortalidade hospitalar em idosos brasileiros. Rev Saude Publica 2023;57(1):12-20. https://doi.org/10.11606/s1518-8787.2023057004567.",
        "Calman JW, Josh MKH, Gehardt JE, et al. Frailty and mortality in older adults. J Am Geriatr Soc 2022;70(4):1001-9. https://doi.org/10.1111/jgs.17800.",
        "Pereira LM, Costa RS, Almeida PQ. Fragilidade e desfechos clínicos em idosos. Cad Saude Publica 2022;38(5):e00123421. https://doi.org/10.1590/0102-311xpt123421.",
        "Smith JA, Brown TK, Wilson RE. Hospital mortality among older people: a cohort study. Age Ageing 2021;50(3):800-7. https://doi.org/10.1093/ageing/afab001.",
        "Garcia MN, Lopez PR, Torres CA. Mortalidad hospitalaria en ancianos. Rev Esp Geriatr Gerontol 2023;58(2):90-5. https://doi.org/10.1016/j.regg.2022.11.004.",
        "Oliveira FG, Santos HJ, Ribeiro KL. Perfil de internações de idosos no SUS. Epidemiol Serv Saude 2024;33:e2023450. https://doi.org/10.1590/s2237-96222024v33e2023450.",
        "Nguyen VT, Tran QH, Le MD. Frailty indices in hospital settings. BMC Geriatr 2023;23:210. https://doi.org/10.1186/s12877-023-03900-1.",
        "Rocha DP, Martins EC, Barros LS. Multimorbidade e mortalidade em idosos. Cienc Saude Colet 2021;26(9):4001-10. https://doi.org/10.1590/1413-81232021269.12345.",
        "Kim SH, Park JY, Lee DW. Nutritional status and mortality in older inpatients. Clin Nutr 2022;41(6):1200-8. https://doi.org/10.1016/j.clnu.2022.04.001.",
        "Ferreira AL, Mendes TR, Cardoso NB. Qualidade dos dados do SIH/SUS. Rev Bras Epidemiol 2021;24:e210030. https://doi.org/10.1590/1980-549720210030.",
        "Johnson KM, Davis LP, Moore RT. Predictors of in-hospital death in the elderly. J Gerontol A 2024;79(1):glad100. https://doi.org/10.1093/gerona/glad100.",
        "Araujo PC, Teixeira JB, Moraes VH. Envelhecimento e uso de serviços de saúde no Brasil. Rev Saude Publica 2022;56:45. https://doi.org/10.11606/s1518-8787.2022056003900.",
        "Ito M, Tanaka Y, Suzuki H. Frailty and outcomes in Japanese hospitals. Geriatr Gerontol Int 2023;23(4):300-6. https://doi.org/10.1111/ggi.14560.",
        "Barbosa CF, Nunes AS, Pinto GM. Mortalidade hospitalar por causas evitáveis em idosos. Cad Saude Publica 2021;37(11):e00200621. https://doi.org/10.1590/0102-311X00200621.",
        "Organização Mundial da Saúde. Relatório mundial sobre envelhecimento e saúde. Genebra: OMS; 2015. Disponível em: https://www.who.int/ageing/publications/world-report-2015/en/",
    ]
    if bad:
        refs[1] = "Calman JW, Josh MKH, Gehardt JE, Parker RJ, et al. Frailty and mortality in older adults. J Am Geriatr Soc 2022;70(4):1001-9. https://doi.org/10.1111/jgs.17800."
        refs[2] = "Pereira L.M., Costa R.S. Fragilidade e desfechos clínicos em idosos. Cad Saude Publica 2022;38(5):e00123421."
    for i, r in enumerate(refs, 1):
        P(f"{i}. {r}", align=AL.LEFT if bad else AL.JUSTIFY, spacing=1.5 if bad else 1.0, after=0)

    doc.save(path)


def build_cover(path: Path):
    doc = Document()
    doc.styles["Normal"].font.name = "Times New Roman"
    doc.styles["Normal"].font.size = Pt(12)
    doc.add_paragraph("Título: Fatores associados à mortalidade em idosos hospitalizados no Brasil")
    people = [("Maria Souza Lima", "0000-0001-2345-6789", "1234567890123456", "@maria.lima",
               "Enfermeira, Doutora em Saúde Coletiva. Doutorado pela UEPG."),
              ("João Pedro Alves", "0000-0002-3456-7890", "9876543210987654", "@joao.alves",
               "Professor, Mestre em Saúde Pública. Mestrado pela UFPR.")]
    for n, o, l, ig, bio in people:
        doc.add_paragraph(f"Autor: {n}")
        doc.add_paragraph(f"ORCID: https://orcid.org/{o}")
        doc.add_paragraph(f"Currículo lattes: http://lattes.cnpq.br/{l}")
        doc.add_paragraph("Afiliação: Universidade Estadual de Ponta Grossa, Ponta Grossa, Paraná, Brasil.")
        doc.add_paragraph(f"Instagram: {ig}")
        doc.add_paragraph(f"Resumo da Biografia: {bio}")
    doc.add_paragraph("Contribuições dos autores:")
    for n, tx in (("Maria Souza Lima", " concepção, análise e interpretação de dados."),
                  ("João Pedro Alves", " redação e revisão crítica do manuscrito.")):
        p = doc.add_paragraph()
        p.add_run(n).bold = True
        p.add_run(tx)
    doc.add_paragraph("Autor Correspondente: Maria Souza Lima")
    doc.add_paragraph("Endereço: Av. Carlos Cavalcanti, 4748, Ponta Grossa, PR. E-mail: maria.lima@uepg.br")
    doc.add_paragraph("Todos os autores aprovaram a versão final.")
    doc.save(path)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "samples")
    out.mkdir(parents=True, exist_ok=True)
    build(out / "manuscrito_bom.docx", bad=False)
    build(out / "manuscrito_ruim.docx", bad=True)
    build_cover(out / "folha_de_rosto.docx")
    print("amostras geradas em", out.resolve())
