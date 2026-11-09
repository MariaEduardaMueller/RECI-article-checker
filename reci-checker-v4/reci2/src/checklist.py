"""Registro das verificações na ORDEM e com as SEÇÕES do Checklist da RECI (check_list_texto_dois.docx)."""
import abbreviations as abbr
import abstracts
import attachments
import body_sections as body
import citations
import conclusion
import cover_page
import descriptors
import manuscript_general_formatting as fmt
import metadata
import ollaminha
import references
import tables_and_figures as tf
import titles
from catalog import BY_ID
from common import Ctx, res

PLAGIO = lambda ctx: res("plag.plagio", "Detecção de plágio ≤ 35%", "SKIP", "Verificado por outro software (fora do escopo deste verificador).")  # noqa: E731

CHECKLIST = [
    ("DETECÇÃO DE PLÁGIO", [("plag.plagio", PLAGIO)]),
    ("DOCUMENTOS OBRIGATÓRIOS", [(i, attachments.make(i, d, rx)) for i, d, rx in attachments.REQUIRED] + [("doc.folha", attachments.item_folha)]),
    ("FOLHA DE ROSTO", [("fr.titulo", cover_page.item_titulo), ("fr.autores", metadata.item_1), ("fr.nomes", metadata.item_2),
                        ("fr.afiliacao", metadata.item_4), ("fr.links", metadata.item_3), ("fr.email", cover_page.item_email),
                        ("fr.biografia", cover_page.item_biografia), ("fr.redes", cover_page.item_redes),
                        ("fr.contribuicoes", cover_page.item_contribuicoes)]),
    ("FORMATAÇÃO GERAL DO MANUSCRITO", [("fg.autoria", fmt.item_fg_autoria), ("fg.formato", fmt.item_fg_formato), ("fg.fonte", fmt.item_fg_fonte),
                                        ("fg.simples", fmt.item_fg_simples), ("fg.italico", fmt.item_fg_italico), ("fg.secoes", fmt.item_fg_secoes),
                                        ("fg.esquerda", fmt.item_fg_esquerda), ("fg.espac_secoes", fmt.item_fg_espac_secoes),
                                        ("fg.recuo", fmt.item_fg_recuo), ("fg.palavras", fmt.item_fg_palavras)]),
    ("TÍTULO DO MANUSCRITO", [("ti.max15", titles.item_ti_max15), ("ti.idiomas", titles.item_ti_idiomas), ("ti.principal", titles.item_ti_principal),
                              ("ti.idioma_trabalho", titles.item_ti_idioma_trabalho), ("ti.secundarios", titles.item_ti_secundarios),
                              ("ti.plataforma", titles.item_ti_plataforma)]),
    ("RESUMOS", [("re.abaixo", abstracts.item_re_abaixo), ("re.conciso", abstracts.item_re_conciso), ("re.resumo", abstracts.item_re_resumo),
                 ("re.abstract", abstracts.item_re_abstract), ("re.resumen", abstracts.item_re_resumen), ("re.autores", abstracts.item_re_autores)]),
    ("DESCRITORES", [("de.abaixo", descriptors.item_de_abaixo), ("de.quantidade", descriptors.item_de_quantidade),
                     ("de.termos", descriptors.item_de_termos), ("de.italico", descriptors.item_de_italico)]),
    ("INTRODUÇÃO", [("in.breve", body.item_in_breve), ("in.objetivo", body.item_in_objetivo), ("in.autores", citations.item_in_autores)]),
    ("MÉTODO", [(i, ollaminha.make_item(i)) for i in ("me.delineamento", "me.cenario", "me.populacao", "me.criterios", "me.fonte", "me.periodo", "me.analise")]
               + [("me.etica", body.item_me_etica), ("me.objetiva", ollaminha.item_me_objetiva), ("me.autores", citations.item_me_autores)]),
    ("ASPECTOS ÉTICOS", [("et.parecer", body.item_et_parecer), ("et.resolucoes", body.item_et_resolucoes),
                         ("et.protocolo", body.item_et_protocolo), ("et.caae", body.item_et_caae)]),
    ("RESULTADOS", [("rs.sequencia", body.item_rs_sequencia), ("rs.ilustracoes", tf.item_rs_ilustracoes)]),
    ("DISCUSSÃO", [("di.limitacoes", body.item_di_limitacoes), ("di.literatura", body.item_di_literatura), ("di.autores", citations.item_di_autores)]),
    ("CONCLUSÃO", [("co.incorporada", conclusion.item_co_incorporada)]),
    ("SÍMBOLOS, ABREVIATURAS E SIGLAS", [("si.siglas", abbr.item_si_siglas), ("si.termos", abbr.item_si_termos)]),
    ("TABELAS", [("tb.max5", tf.item_tb_max5), ("tb.editaveis", tf.item_tb_editaveis), ("tb.titulo", tf.item_tb_titulo),
                 ("tb.citacao", tf.item_tb_citacao), ("tb.linhas", tf.item_tb_linhas), ("tb.word", tf.item_tb_word),
                 ("tb.n_pct", tf.item_tb_n_pct), ("tb.siglas", tf.item_tb_siglas), ("tb.total", tf.item_tb_total),
                 ("tb.explicativo", tf.item_tb_explicativo)]),
    ("FIGURAS (GRÁFICOS, MAPAS, etc.)", [("fi.qualidade", tf.item_fi_qualidade), ("fi.titulo", tf.item_fi_titulo), ("fi.centralizada", tf.item_fi_centralizada),
                                         ("fi.cor", tf.item_fi_cor), ("fi.graf_titulo", tf.item_fi_graf_titulo), ("fi.citacao", tf.item_fi_citacao),
                                         ("fi.explicativo", tf.item_fi_explicativo)]),
    ("REFERÊNCIAS AO LONGO DO TEXTO", [("rt.citacoes", citations.item_rt_citacoes), ("rt.autores", citations.item_rt_autores)]),
    ("REFERÊNCIAS", [("rf.vancouver", references.item_rf_vancouver), ("rf.formato", references.item_rf_formato),
                     ("rf.internacionais", references.item_rf_internacionais), ("rf.recentes", references.item_rf_recentes),
                     ("rf.doi", references.item_rf_doi), ("rf.autores", references.item_rf_autores), ("rf.etal", references.item_rf_etal)]),
]
CATEGORY = ("cat.refs", references.item_cat_refs)

# Linhas do Checklist que dependem de julgamento humano
MANUAL = [
    "Ortografia oficial (revisão ortográfica/gramatical)",
    "Título inédito, claro e conciso; título cadastrado em inglês na plataforma (equipe RECI)",
    "Descritores conforme o DeCS/BIREME (decs.bvsalud.org)",
    "Introdução breve, com revisão da literatura e justificativa; objetivo coerente com a proposta",
    "Informações dos Métodos objetivas e completas; resultados em sequência lógica",
    "Resultados comparados com a literatura e adequadamente discutidos; conclusão responde aos objetivos",
    "Tabelas claras; abreviação dos periódicos (Index Medicus/MedLine)",
]


def run_all(ctx: Ctx):
    """Executa todas as verificações; erros viram status '-' sem interromper o relatório. -> (categoria, seções)"""
    def safe(item, fn):
        try:
            r = fn(ctx)
        except Exception as e:  # noqa: BLE001
            r = res(item, BY_ID[item].text if item in BY_ID else item, "-", f"Erro interno: {type(e).__name__}: {e}")
        r["item"] = item
        return r

    cat = safe(*CATEGORY)
    out = []
    for section, checks in CHECKLIST:
        out.append((section, [safe(i, fn) for i, fn in checks]))
    return cat, out
