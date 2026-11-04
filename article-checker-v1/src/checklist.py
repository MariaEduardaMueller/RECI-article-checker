"""Registro das verificações na ORDEM e com as SEÇÕES do Checklist da RECI."""
import abstracts, abbreviations, attachments, body_sections, citations, conclusion, cover_page, descriptors
import manuscript_general_formatting as fmt
import metadata, ollaminha, references, tables_and_figures as tf, titles
from common import Ctx, res

CHECKLIST = [
    ("CATEGORIA DO MANUSCRITO – Artigo Original", [(100, references.item_100)]),
    ("METADADOS", [(1, metadata.item_1), (2, metadata.item_2), (3, metadata.item_3), (4, metadata.item_4), (5, cover_page.item_5)]),
    ("DOCUMENTOS OBRIGATÓRIOS", [(n, attachments.make(n, d, rx)) for n, d, rx in attachments.REQUIRED] + [(106, attachments.item_106)]),
    ("FOLHA DE ROSTO", [(109, cover_page.item_109), (10, cover_page.item_10), (107, cover_page.item_107),
                        (108, cover_page.item_108), (11, cover_page.item_11)]),
    ("FORMATAÇÃO GERAL DO MANUSCRITO", [(12, fmt.item_12), (13, fmt.item_13), (14, fmt.item_14), (110, fmt.item_110),
                                        (16, fmt.item_16), (111, fmt.item_111), (18, fmt.item_18)]),
    ("TÍTULOS", [(19, titles.item_19), (23, titles.item_23), (20, titles.item_20), (21, titles.item_21), (112, titles.item_112)]),
    ("RESUMOS", [(113, abstracts.item_113), (24, abstracts.item_24), (25, abstracts.item_25), (26, abstracts.item_26),
                 (27, abstracts.item_27), (28, abstracts.item_28)]),
    ("DESCRITORES", [(30, descriptors.item_30), (31, descriptors.item_31), (32, descriptors.item_32), (33, descriptors.item_33)]),
    ("INTRODUÇÃO", [(114, body_sections.item_114), (115, body_sections.item_115)]),
    ("MÉTODO", [(n, ollaminha.make_item(n)) for n in range(36, 43)] + [(116, body_sections.item_116)]),
    ("ASPECTOS ÉTICOS", [(117, body_sections.item_117), (118, body_sections.item_118), (119, body_sections.item_119), (120, body_sections.item_120)]),
    ("RESULTADOS", [(121, tf.item_121), (122, tf.item_122)]),
    ("DISCUSSÃO", [(123, references.item_123), (124, body_sections.item_124)]),
    ("CONCLUSÃO", [(53, conclusion.item_53)]),
    ("SÍMBOLOS, ABREVIATURAS E SIGLAS", [(125, abbreviations.item_125), (126, abbreviations.item_126)]),
    ("TABELAS, QUADROS E GRÁFICOS", [(54, tf.item_54), (58, tf.item_58), (127, tf.item_127), (128, tf.item_128), (129, tf.item_129),
                                     (130, tf.item_130), (61, tf.item_61), (132, tf.item_132), (133, tf.item_133), (131, tf.item_131)]),
    ("REFERÊNCIAS AO LONGO DO TEXTO", [(134, citations.item_134), (135, citations.item_135)]),
    ("REFERÊNCIAS", [(66, references.item_66), (136, citations.item_136), (69, references.item_69), (137, references.item_137),
                     (71, references.item_71), (72, references.item_72), (73, references.item_73)]),
]

# Linhas do Checklist que dependem de julgamento humano
MANUAL = [
    "Redigido na ortografia oficial (revisão ortográfica/gramatical)",
    "Título inédito, claro e conciso; título cadastrado em inglês na plataforma",
    "Descritores conforme o DeCS/BIREME (decs.bvsalud.org)",
    "Introdução breve, com revisão da literatura e justificativa; objetivo coerente com a proposta",
    "Informações dos Métodos descritas de forma objetiva e completa",
    "Resultados em sequência lógica; tabelas claras e que transmitem os dados",
    "Abreviação dos periódicos conforme Index Medicus/BVS",
    "Gráficos padronizados na cor preta",
]


def run_all(ctx: Ctx):
    """Executa todas as verificações; erros viram status '-' sem interromper o relatório."""
    out = []
    for section, checks in CHECKLIST:
        results = []
        for item, fn in checks:
            try:
                r = fn(ctx)
            except Exception as e:
                r = res(item, getattr(fn, "__doc__", None) or f"Item {item}", "-", f"Erro interno: {type(e).__name__}: {e}")
            results.append(r)
        out.append((section, results))
    return out
