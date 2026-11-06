"""INTRODUÇÃO, MÉTODOS (ética), RESULTADOS e DISCUSSÃO."""
import re

from common import Ctx, fmt_list, n_words, note, res, strip_accents
from abstracts import abstract_content

_STOP = {"geral", "principal", "especifico", "especificos", "deste", "desta", "neste", "nesta", "desse", "dessa", "do", "da",
         "de", "dos", "das", "estudo", "pesquisa", "trabalho", "artigo", "e", "foi", "foram", "sao", "era", "como", "o", "a",
         "os", "as", "se", "um", "uma", "presente", "este", "esta", "proposto", "central", "que"}
_WORD = re.compile(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)?")


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú])", text) if s.strip()]


OBJ = re.compile(r"\bobjetivos?\b|\bobjetivou(?:-se)?\b|\bobjetivam\b|\bobjetiva-se\b", re.IGNORECASE)


def find_objective(text):
    """(sentença, verbo, trecho-do-objetivo). Prefere ocorrências seguidas de verbo no infinitivo."""
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


def _tokens(text):
    return {strip_accents(w.lower()) for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", text)} - {"estudo", "objetivo", "objetivou", "este", "esta"}


def item_in_breve(ctx: Ctx):
    desc = "Breve, apresenta a revisão da literatura, justificativa e objetivo"
    intro = ctx.sections.get("INTRODUCTION")
    if not intro:
        return res("in.breve", desc, "-", "Introdução não encontrada")
    n = sum(n_words(p.stripped) for p in intro)
    if n > 1000:
        return res("in.breve", desc, "AP", f"{n} palavras: introdução extensa para o formato 'breve'. Conteúdo (revisão, justificativa) deve ser avaliado manualmente.",
                   [note(intro[0], f"Introdução com {n} palavras: torne-a mais breve (revisão da literatura, justificativa e objetivo).")])
    return res("in.breve", desc, "-", f"{n} palavras. Revisão da literatura, justificativa e objetivo devem ser avaliados manualmente.")


def item_in_objetivo(ctx: Ctx):
    desc = "O objetivo é coerente com a proposta do estudo, idêntico ao apresentado no resumo, destacado no último parágrafo da introdução e iniciado por verbo no infinitivo"
    intro = ctx.sections.get("INTRODUCTION")
    if not intro:
        return res("in.objetivo", desc, "-", "Introdução não encontrada")
    sent, verb, _ = find_objective(intro[-1].text)
    in_last = sent is not None
    para = intro[-1]
    if not in_last:
        for p in intro[:-1]:
            sent, verb, _ = find_objective(p.text)
            if sent:
                para = p
                break
    if not sent:
        return res("in.objetivo", desc, "NA", "Objetivo não identificado na Introdução (use, por ex., 'O objetivo deste estudo foi analisar...')",
                   [note(intro[-1], "Destaque aqui o objetivo do estudo, iniciado por verbo no infinitivo (ex.: “O objetivo foi analisar...”).")])
    msgs, notes = [], []
    if not in_last:
        msgs.append(f"objetivo está em {ctx.where(para)}, não no último parágrafo")
        notes.append(note(para, "O objetivo deve ficar no último parágrafo da Introdução."))
    if not is_infinitive(verb):
        msgs.append(f"objetivo não inicia com verbo no infinitivo (encontrado '{verb}')")
        notes.append(note(para, f"O objetivo deve ser iniciado por verbo no infinitivo (encontrado “{verb}”)."))
    clause = find_objective(para.text)[2]
    paras = abstract_content(ctx, "RESUMO")
    cov = None
    if paras and clause:
        full = " ".join(p.text for p in paras)
        m = re.search(r"Justificativa e Objetivos:(.*?)(?:Métodos:|Metodologia:|$)", full, re.DOTALL | re.IGNORECASE)
        seg = m.group(1) if m else full
        a, b = _tokens(clause), _tokens(find_objective(seg)[2] or seg)
        cov = len(a & b) / len(a) if a else 0
        if cov < 0.7:
            msgs.append(f"objetivo difere do resumo ({cov:.0%} das palavras-chave em comum)")
            notes.append(note(para, f"O objetivo deve ser idêntico ao apresentado no resumo (apenas {cov:.0%} de correspondência)."))
    if not msgs:
        return res("in.objetivo", desc, "A", f"Objetivo no último parágrafo, com verbo '{verb}'" + (f"; {cov:.0%} de correspondência com o resumo" if cov is not None else "") + ". Coerência com o estudo deve ser avaliada manualmente.")
    bad = len(msgs) >= 2 or any("infinitivo" in m for m in msgs)
    return res("in.objetivo", desc, "NA" if bad and len(msgs) >= 2 else "AP", "; ".join(msgs), notes)


# ----------------------------- ÉTICA ----------------------------------------------------
ETHICS_KW = re.compile(r"[ée]tic|\bCEP\b|comit[êe]|CAAE|resolu[çc][ãa]o|parecer|protocolo|consentimento|TCLE|CONEP|dispens", re.IGNORECASE)
WAIVER = re.compile(
    r"dados\s+(?:secund[aá]rios\s+)?(?:de\s+)?(?:dom[ií]nio\s+p[uú]blico|p[uú]blicos|agregados)|"
    r"dispens\w+\s+(?:de\s+|do\s+|da\s+)?(?:apreci|submiss|aprova|parecer|avalia|registro|n[uú]mero|CAAE|CEP|comit)|"
    r"(?:parecer|CAAE|CEP|protocolo|n[uú]mero|registro)[^.]{0,60}dispensad|"
    r"n[ãa]o\s+(?:foi\s+|ser[áa]\s+)?(?:necess|exig|envolv|requer|precis)\w+[^.]{0,70}(?:CEP|CAAE|comit[êe]|seres\s+humanos|apreci|parecer|aprova)|"
    r"sem\s+envolvimento\s+de\s+seres\s+humanos|n[ãa]o\s+envolve\s+seres\s+humanos|art(?:igo|\.)\s*1[º°]?[^.]{0,30}510", re.IGNORECASE)
DATE = re.compile(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b|\b\d{1,2}\s+de\s+[a-zç]+\s+de\s+\d{4}\b|"
                  r"\b(?:em|data)\s*(?:de\s+)?(?:[a-zç]+\s+de\s+)?\d{4}\b", re.IGNORECASE)


def _methods(ctx):
    return ctx.sections.get("METHODS")


def _ethics_text(ctx):
    M = _methods(ctx)
    return " ".join(s for p in M for s in _sentences(p.text) if ETHICS_KW.search(s)), M


def waiver_kinds(ctx: Ctx) -> set:
    """O que o texto declara dispensado? 'cep' (apreciação ética/parecer: tudo), 'protocolo' (número e data do parecer) ou 'caae'."""
    kinds = set()
    for p in _methods(ctx):
        for s in _sentences(p.text):
            if not WAIVER.search(s):
                continue
            if re.search(r"CAAE", s, re.I):
                kinds.add("caae")
            elif re.search(r"n[uú]mero|data|protocolo|registro", s, re.I) and not re.search(r"seres\s+humanos|dom[ií]nio|p[uú]blic|apreci", s, re.I):
                kinds.add("protocolo")
            else:
                kinds.add("cep")
    return kinds


def waived(ctx: Ctx, what: str = "cep") -> bool:
    """O texto dispensa `what`? 'cep' dispensa tudo; 'protocolo' dispensa também o CAAE."""
    k = waiver_kinds(ctx)
    if "cep" in k:
        return True
    return (what == "protocolo" and "protocolo" in k) or (what == "caae" and bool(k & {"caae", "protocolo"}))


def _w(ctx):  # (frase de dispensa) para citar no comentário
    t = " ".join(p.text for p in _methods(ctx))
    m = WAIVER.search(t)
    if not m:
        return ""
    sent = next((x for x in _sentences(t) if WAIVER.search(x)), t[m.start():m.end()])
    return f"“{sent[:140]}”"


def item_me_etica(ctx: Ctx):
    desc = "Considerações éticas devem estar descritas no último parágrafo da seção de métodos"
    M = _methods(ctx)
    if not M:
        return res("me.etica", desc, "-", "Métodos não encontrados")
    if ETHICS_KW.search(M[-1].text):
        return res("me.etica", desc, "A", "Considerações éticas no último parágrafo de Métodos")
    if any(ETHICS_KW.search(p.text) for p in M):
        return res("me.etica", desc, "AP", "Considerações éticas presentes, mas não no último parágrafo de Métodos",
                   [note(next(p for p in M if ETHICS_KW.search(p.text)), "Mova as considerações éticas para o último parágrafo da seção de Métodos.")])
    return res("me.etica", desc, "NA", "Considerações éticas não encontradas em Métodos: acrescente-as no último parágrafo.",
               [note(M[-1], "Acrescente aqui (último parágrafo de Métodos) as considerações éticas: parecer do CEP, CAAE e resoluções.")])


def item_et_parecer(ctx: Ctx):
    desc = "Para estudos com seres humanos, indica no último parágrafo do método o parecer CEP"
    et, M = _ethics_text(ctx)
    if not M:
        return res("et.parecer", desc, "-", "Métodos não encontrados")
    if re.search(r"comit[êe]\s+de\s+[ée]tica|\bCEP\b", et, re.IGNORECASE) and re.search(r"parecer|aprova|protocolo|CAAE", et, re.IGNORECASE):
        return res("et.parecer", desc, "A", "Parecer/aprovação do CEP indicado")
    if waived(ctx):
        return res("et.parecer", desc, "NSA", f"O manuscrito declara dispensa de apreciação ética: {_w(ctx)}")
    return res("et.parecer", desc, "NA", "Parecer do CEP não indicado em Métodos: informe o Comitê de Ética em Pesquisa e o parecer, ou declare a dispensa.",
               [note(M[-1], "Indique aqui o parecer do Comitê de Ética em Pesquisa (CEP) ou declare a dispensa de apreciação ética.")])


def item_et_resolucoes(ctx: Ctx):
    desc = "Apresenta que a pesquisa foi conduzida de acordo com os padrões éticos exigidos - Resoluções 466/2012 - 510/2016 - 580/2018, do Ministério da Saúde"
    et, M = _ethics_text(ctx)
    if not M:
        return res("et.resolucoes", desc, "-", "Métodos não encontrados")
    txt = " ".join(p.text for p in M)
    found = sorted(set(re.findall(r"\b(466|510|580)\b", txt))) if re.search(r"Resolu", txt, re.IGNORECASE) else []
    if found:
        return res("et.resolucoes", desc, "A", "Resolução(ões) citada(s): " + ", ".join(found))
    if waived(ctx):
        return res("et.resolucoes", desc, "NSA", f"Estudo com dispensa de apreciação ética: {_w(ctx)}")
    return res("et.resolucoes", desc, "NA", "Nenhuma das Resoluções 466/2012, 510/2016 ou 580/2018 foi citada em Métodos",
               [note(M[-1], "Informe que a pesquisa seguiu as Resoluções 466/2012, 510/2016 ou 580/2018 do Ministério da Saúde.")])


def item_et_protocolo(ctx: Ctx):
    desc = "Apresenta o número do protocolo de aprovação e a data de aprovação no Comitê de Ética em Pesquisa"
    et, M = _ethics_text(ctx)
    if not M:
        return res("et.protocolo", desc, "-", "Métodos não encontrados")
    if not et and waived(ctx, "protocolo"):
        return res("et.protocolo", desc, "NSA", f"Estudo com dispensa de apreciação ética: {_w(ctx)}")
    proto = re.search(r"(?:parecer|protocolo|aprova\w+)[^.;]{0,40}?\d[\d.\-/]{3,}|CAAE[^.;]{0,15}\d{8}", et, re.IGNORECASE)
    date = DATE.search(re.sub(r"CAAE[\s:nº°.]*[\d.]+", "", et))
    if proto and date:
        return res("et.protocolo", desc, "A", "Número do protocolo/parecer e data de aprovação encontrados")
    if waived(ctx, "protocolo"):
        return res("et.protocolo", desc, "NSA", f"O manuscrito declara dispensa do número/data do parecer: {_w(ctx)}")
    target = M[-1]
    miss = "a data de aprovação" if proto else ("o número do protocolo/parecer" if date else "o número do protocolo/parecer e a data de aprovação")
    return res("et.protocolo", desc, "AP" if (proto or date) else "NA", f"Falta {miss} (último parágrafo de Métodos)",
               [note(target, f"Informe {miss} no CEP.")])


def item_et_caae(ctx: Ctx):
    desc = "O número do CAAE (Certificado de Apresentação de Apreciação Ética) foi adicionado nos Métodos"
    M = _methods(ctx)
    if not M:
        return res("et.caae", desc, "-", "Métodos não encontrados")
    t = " ".join(p.text for p in M)
    if re.search(r"\b\d{8}\.\d\.\d{4}\.\d{4}\b", t):
        return res("et.caae", desc, "A", "CAAE no formato 00000000.0.0000.0000")
    if waived(ctx, "caae"):
        return res("et.caae", desc, "NSA", f"O manuscrito declara dispensa do CAAE/apreciação ética: {_w(ctx)}")
    if re.search(r"CAAE", t, re.IGNORECASE):
        p = next(p for p in M if re.search("CAAE", p.text, re.I))
        return res("et.caae", desc, "AP", "CAAE mencionado, mas fora do formato 00000000.0.0000.0000",
                   [note(p, "Informe o CAAE no formato 00000000.0.0000.0000.")])
    return res("et.caae", desc, "NA", "CAAE não encontrado em Métodos (nem declaração de dispensa)",
               [note(M[-1], "Informe o número do CAAE (00000000.0.0000.0000) ou declare a dispensa de apreciação ética.")])


# ----------------------------- RESULTADOS / DISCUSSÃO --------------------------------------------
def item_rs_sequencia(ctx: Ctx):
    return res("rs.sequencia", "Os resultados estão descritos em sequência lógica", "-", "Avaliação manual (sequência lógica dos resultados)")


def item_di_literatura(ctx: Ctx):
    return res("di.literatura", "Apresenta os resultados comparados com os resultados da literatura e adequadamente discutidos", "-", "Avaliação manual (comparação com a literatura)")


def item_di_limitacoes(ctx: Ctx):
    desc = "Indica no penúltimo parágrafo as limitações do estudo e formas de mitigação"
    D = ctx.sections.get("DISCUSSION")
    if len(D) < 2:
        return res("di.limitacoes", desc, "-" if not D else "NA", "Discussão não encontrada ou com menos de dois parágrafos")
    lim = re.compile(r"limita[çc]|barreira|dificuldade|vi[eé]s\b|restri[çc][ãa]o", re.IGNORECASE)
    mit = re.compile(r"mitig|minimiz|reduz|control|sugere-se|recomenda-se|estudos\s+futuros|pesquisas\s+futuras|valida|ampliar|futuros?\s+estudos", re.IGNORECASE)
    pen = D[-2]
    if lim.search(pen.text):
        if mit.search(pen.text):
            return res("di.limitacoes", desc, "A", "Limitações e formas de mitigação no penúltimo parágrafo")
        return res("di.limitacoes", desc, "AP", f"Limitações no penúltimo parágrafo ({ctx.where(pen)}), sem formas de mitigação",
                   [note(pen, "Inclua as formas de mitigação das limitações do estudo.")])
    where = [i for i, p in enumerate(D) if lim.search(p.text)]
    if where:
        return res("di.limitacoes", desc, "AP", f"Limitações citadas em {ctx.where(D[where[0]])}, mas devem estar no penúltimo parágrafo ({ctx.where(pen)})",
                   [note(D[where[0]], "As limitações do estudo e as formas de mitigação devem estar no penúltimo parágrafo da Discussão.")])
    return res("di.limitacoes", desc, "NA", f"Limitações do estudo não encontradas na Discussão: acrescente-as no penúltimo parágrafo ({ctx.where(pen)})",
               [note(pen, "Descreva aqui (penúltimo parágrafo) as limitações do estudo e as formas de mitigação.")])
