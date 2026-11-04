"""INTRODUÇÃO, MÉTODOS (ética) e DISCUSSÃO — itens 114 a 120 e 124."""
import re

from common import Ctx, fmt_list, res, strip_accents
from abstracts import abstract_content

_STOP = {"geral", "principal", "especifico", "especificos", "deste", "desta", "neste", "nesta", "desse", "dessa", "do", "da",
         "de", "dos", "das", "estudo", "pesquisa", "trabalho", "artigo", "e", "foi", "foram", "sao", "era", "como", "o", "a",
         "os", "as", "se", "um", "uma", "presente", "este", "esta", "proposto", "central", "que"}
_WORD = re.compile(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)?")


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú])", text) if s.strip()]


OBJ = re.compile(r"\bobjetivos?\b|\bobjetivou(?:-se)?\b|\bobjetivam\b|\bobjetiva-se\b", re.IGNORECASE)


def find_objective(text):
    """Devolve (sentença, verbo, trecho-do-objetivo). Prefere ocorrências seguidas de verbo no infinitivo."""
    fallback = (None, None, None)
    for s in _sentences(text):
        for m in OBJ.finditer(s):
            for w in _WORD.finditer(s, m.end()):
                if strip_accents(w.group(0).lower()) not in _STOP:
                    cand = (s, w.group(0), s[w.start():])
                    if is_infinitive(w.group(0)):
                        return cand
                    if fallback[0] is None:
                        fallback = cand
                    break
    return fallback


def is_infinitive(w):
    return bool(w) and bool(re.fullmatch(r"[a-zà-ÿ]{3,}(?:ar|er|ir|or|ôr)(?:-se)?", w.lower()))


def item_114(ctx: Ctx):
    desc = ("O objetivo é coerente com o estudo, destacado no último parágrafo da introdução e iniciado por verbo no infinitivo")
    intro = ctx.sections.get("INTRODUCTION")
    if not intro:
        return res(114, desc, "-", "Introdução não encontrada")
    sent, verb, _ = find_objective(intro[-1].text)
    in_last = sent is not None
    if not in_last:
        for p in intro[:-1]:
            sent, verb, _ = find_objective(p.text)
            if sent:
                break
    if not sent:
        return res(114, desc, "NA", "Objetivo não identificado na Introdução (use, por ex., 'O objetivo deste estudo foi analisar...')")
    msgs = []
    if not in_last:
        msgs.append("objetivo não está no último parágrafo da Introdução")
    if not is_infinitive(verb):
        msgs.append(f"objetivo não inicia com verbo no infinitivo (encontrado '{verb}')")
    return res(114, desc, ("AP" if len(msgs) == 1 else "NA") if msgs else "A", "; ".join(msgs) if msgs else f"Objetivo no último parágrafo, com verbo '{verb}'. Coerência com o estudo deve ser avaliada manualmente.")


def _tokens(text):
    return {strip_accents(w.lower()) for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", text)} - {"estudo", "objetivo", "objetivou", "este", "esta"}


def item_115(ctx: Ctx):
    desc = "O objetivo é idêntico ao apresentado no resumo"
    intro = ctx.sections.get("INTRODUCTION")
    paras = abstract_content(ctx, "RESUMO")
    if not intro or not paras:
        return res(115, desc, "-", "Introdução ou RESUMO não encontrados")
    clause = next((find_objective(p.text)[2] for p in reversed(intro) if find_objective(p.text)[0]), None)
    if not clause:
        return res(115, desc, "-", "Objetivo da Introdução não identificado")
    full = " ".join(p.text for p in paras)
    m = re.search(r"Justificativa e Objetivos:(.*?)(?:Métodos:|Metodologia:|$)", full, re.DOTALL | re.IGNORECASE)
    seg = m.group(1) if m else full
    abs_clause = find_objective(seg)[2] or seg
    a, b = _tokens(clause), _tokens(abs_clause)
    cov = len(a & b) / len(a) if a else 0
    msg = f"{cov:.0%} das palavras-chave do objetivo da Introdução aparecem no objetivo do RESUMO"
    return res(115, desc, "A" if cov >= 0.7 else "AP" if cov >= 0.4 else "NA", msg)


# ----------------------------- ÉTICA ----------------------------------------------------
ETHICS_KW = re.compile(r"[ée]tic|\bCEP\b|comit[êe]|CAAE|resolu[çc][ãa]o|parecer|protocolo|consentimento|TCLE|CONEP|dispens", re.IGNORECASE)
WAIVER = re.compile(r"dados\s+(?:secund[aá]rios\s+)?(?:de\s+)?(?:dom[ií]nio\s+p[uú]blico|p[uú]blicos|agregados)|"
                    r"dispens\w+\s+(?:de\s+)?(?:apreci|submiss|aprova|parecer|avalia|registro)|"
                    r"n[ãa]o\s+(?:foi\s+)?(?:necess|exig|envolv)\w+.{0,70}(?:CEP|comit[êe]|seres\s+humanos|apreci)|"
                    r"sem\s+envolvimento\s+de\s+seres\s+humanos|n[ãa]o\s+envolve\s+seres\s+humanos", re.IGNORECASE)
DATE = re.compile(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b|\b\d{1,2}\s+de\s+[a-zç]+\s+de\s+\d{4}\b|"
                  r"\b(?:em|data)\s*(?:de\s+)?(?:[a-zç]+\s+de\s+)?\d{4}\b", re.IGNORECASE)


def _methods(ctx):
    return ctx.sections.get("METHODS")


def _ethics_text(ctx):
    M = _methods(ctx)
    sents = [s for p in M for s in _sentences(p.text) if ETHICS_KW.search(s)]
    return " ".join(sents), M


def _waived(ctx):
    M = _methods(ctx)
    return bool(WAIVER.search(" ".join(p.text for p in M)))


def item_116(ctx: Ctx):
    desc = "Considerações éticas descritas no último parágrafo da seção de métodos"
    M = _methods(ctx)
    if not M:
        return res(116, desc, "-", "Métodos não encontrados")
    if ETHICS_KW.search(M[-1].text):
        return res(116, desc, "A", "Considerações éticas no último parágrafo de Métodos")
    if any(ETHICS_KW.search(p.text) for p in M):
        return res(116, desc, "AP", "Considerações éticas presentes, mas não no último parágrafo de Métodos")
    return res(116, desc, "NA", "Considerações éticas não encontradas em Métodos")


def item_117(ctx: Ctx):
    desc = "Para estudos com seres humanos, indica no último parágrafo do método o parecer do CEP"
    et, M = _ethics_text(ctx)
    if not M:
        return res(117, desc, "-", "Métodos não encontrados")
    if re.search(r"comit[êe]\s+de\s+[ée]tica|\bCEP\b", et, re.IGNORECASE) and re.search(r"parecer|aprova|protocolo|CAAE", et, re.IGNORECASE):
        return res(117, desc, "A", "Parecer/aprovação do CEP indicado")
    if _waived(ctx):
        return res(117, desc, "NSA", "Métodos indicam dispensa de apreciação ética / dados públicos")
    return res(117, desc, "NA", "Parecer do CEP não indicado em Métodos")


def item_118(ctx: Ctx):
    desc = "Pesquisa conduzida segundo os padrões éticos — Resoluções 466/2012, 510/2016 ou 580/2018 do Ministério da Saúde"
    et, M = _ethics_text(ctx)
    if not M:
        return res(118, desc, "-", "Métodos não encontrados")
    txt = " ".join(p.text for p in M)
    found = sorted(set(re.findall(r"\b(466|510|580)\b", txt))) if re.search(r"Resolu", txt, re.IGNORECASE) else []
    if found:
        return res(118, desc, "A", "Resolução(ões) citada(s): " + ", ".join(found))
    if _waived(ctx):
        return res(118, desc, "NSA", "Estudo com dispensa de apreciação ética")
    return res(118, desc, "NA", "Nenhuma das Resoluções 466/2012, 510/2016 ou 580/2018 foi citada")


def item_119(ctx: Ctx):
    desc = "Apresenta o número do protocolo de aprovação e a data de aprovação no CEP"
    et, M = _ethics_text(ctx)
    if not M:
        return res(119, desc, "-", "Métodos não encontrados")
    if not et and _waived(ctx):
        return res(119, desc, "NSA", "Estudo com dispensa de apreciação ética")
    proto = re.search(r"(?:parecer|protocolo|aprova\w+)[^.;]{0,40}?\d[\d.\-/]{3,}|CAAE[^.;]{0,15}\d{8}", et, re.IGNORECASE)
    date = DATE.search(re.sub(r"CAAE[\s:nº°.]*[\d.]+", "", et))
    if proto and date:
        return res(119, desc, "A", "Número do protocolo/parecer e data de aprovação encontrados")
    if proto or date:
        return res(119, desc, "AP", "Falta " + ("a data de aprovação" if proto else "o número do protocolo/parecer"))
    return res(119, desc, "NSA" if _waived(ctx) else "NA", "Protocolo e data de aprovação não encontrados")


def item_120(ctx: Ctx):
    desc = "O número do CAAE foi adicionado nos Métodos"
    M = _methods(ctx)
    if not M:
        return res(120, desc, "-", "Métodos não encontrados")
    t = " ".join(p.text for p in M)
    if re.search(r"\b\d{8}\.\d\.\d{4}\.\d{4}\b", t):
        return res(120, desc, "A", "CAAE no formato 00000000.0.0000.0000")
    if re.search(r"CAAE", t, re.IGNORECASE):
        return res(120, desc, "AP", "CAAE mencionado, mas fora do formato 00000000.0.0000.0000")
    return res(120, desc, "NSA" if _waived(ctx) else "NA", "CAAE não encontrado em Métodos")


# ----------------------------- DISCUSSÃO ------------------------------------------------
def item_124(ctx: Ctx):
    desc = "Indica no penúltimo parágrafo as limitações do estudo e formas de mitigação"
    D = ctx.sections.get("DISCUSSION")
    if len(D) < 2:
        return res(124, desc, "-" if not D else "NA", "Discussão não encontrada ou com menos de dois parágrafos")
    lim = re.compile(r"limita[çc]|barreira|dificuldade|vi[eé]s\b|restri[çc][ãa]o", re.IGNORECASE)
    mit = re.compile(r"mitig|minimiz|reduz|control|sugere-se|recomenda-se|estudos\s+futuros|pesquisas\s+futuras|valida|ampliar|futuros?\s+estudos", re.IGNORECASE)
    pen = D[-2].text
    if lim.search(pen):
        if mit.search(pen):
            return res(124, desc, "A", "Limitações e formas de mitigação no penúltimo parágrafo")
        return res(124, desc, "AP", "Limitações no penúltimo parágrafo, sem formas de mitigação")
    where = [i + 1 for i, p in enumerate(D) if lim.search(p.text)]
    if where:
        return res(124, desc, "AP", f"Limitações citadas, mas não no penúltimo parágrafo (parágrafo(s) {where} de {len(D)})")
    return res(124, desc, "NA", "Limitações do estudo não encontradas na Discussão")
