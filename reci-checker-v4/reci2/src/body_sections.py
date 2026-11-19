"""INTRODUÇÃO, MÉTODOS (ética), RESULTADOS e DISCUSSÃO — artigos em português, inglês e espanhol."""
import re

from abstracts import abstract_content
from common import ABSTRACT_OF_LANG, Ctx, fmt_list, n_words, note, res, strip_accents, work_lang

_STOP = {"geral", "principal", "especifico", "especificos", "deste", "desta", "neste", "nesta", "desse", "dessa", "do", "da",
         "de", "dos", "das", "estudo", "pesquisa", "trabalho", "artigo", "e", "foi", "foram", "sao", "era", "como", "o", "a",
         "os", "as", "se", "um", "uma", "presente", "este", "esta", "proposto", "central", "que",
         # espanhol
         "el", "la", "del", "fue", "es", "estudio", "investigacion", "trabajo", "articulo", "este", "esta", "presente", "principal",
         "general", "especifico", "los", "las", "un", "una", "y", "sido", "son", "fueron"}
_WORD = re.compile(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)?")


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú])", text) if s.strip()]


OBJ = re.compile(r"\bobjetivos?\b|\bobjetivou(?:-se)?\b|\bobjetivam\b|\bobjetiva-se\b|\bprop[oó]sito\b|\bse propuso\b", re.IGNORECASE)
OBJ_EN = re.compile(r"\b(?:aim(?:s|ed)?|objectives?|purposes?|goals?)\b", re.IGNORECASE)


def find_objective(text):
    """(sentença, verbo, trecho-do-objetivo). Português/espanhol: verbo no infinitivo após 'objetivo'; inglês: 'aim/objective ... to <verb>'."""
    fallback = (None, None, None)
    for s in _sentences(text):
        for m in OBJ_EN.finditer(s):                              # inglês: "The aim of this study was to describe ..."
            t = re.search(r"\bto\s+([a-z]{3,})\b", s[m.end():], re.IGNORECASE)
            if t:
                start = m.end() + t.start(1)
                return (s, "to " + t.group(1), s[start:])
        for m in OBJ.finditer(s):                                 # português / espanhol
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
    if not w:
        return False
    if w.lower().startswith("to "):                               # inglês
        return True
    return bool(re.fullmatch(r"[a-zà-ÿ]{3,}(?:ar|er|ir|or|ôr)(?:-se|se|lo|la)?", w.lower()))


_EN_STOP = {"study", "aim", "aims", "aimed", "objective", "objectives", "purpose", "this", "that", "with", "from", "were", "have", "been", "their", "which"}


def _tokens(text):
    return {strip_accents(w.lower()) for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", text)} - {"estudo", "objetivo", "objetivou", "este", "esta"} - _EN_STOP


_OBJ_LABEL = {"RESUMO": r"Justificativa e Objetivos", "ABSTRACT": r"Background and Objectives", "RESUMEN": r"Justificaci[oó]n y Objetivos"}
_NEXT_LABEL = r"(?:M[ée]todos?|Methods?|Metodolog[ií]a)\s*:"


def abstract_objective(ctx: Ctx, n_chars: int = 700):
    """Trecho 'Justificativa e Objetivos' do resumo NO IDIOMA DO ARTIGO (RESUMO, ABSTRACT ou RESUMEN)."""
    key = ABSTRACT_OF_LANG[work_lang(ctx)]
    paras = abstract_content(ctx, key) or abstract_content(ctx, "RESUMO")
    if not paras:
        return None, key
    full = " ".join(p.text for p in paras)
    m = re.search(rf"(?:{_OBJ_LABEL[key]})\s*:(.*?)(?={_NEXT_LABEL}|$)", full, re.DOTALL | re.IGNORECASE)
    return (m.group(1) if m else full)[:n_chars].strip(), key


# ----------------------------- INTRODUÇÃO ---------------------------------------------------
def item_in_breve(ctx: Ctx):
    desc = "Breve, apresenta a revisão da literatura, justificativa e objetivo."
    intro = ctx.sections.get("INTRODUCTION")
    if not intro:
        return res("in.breve", desc, "-", "Introdução não encontrada")
    n = sum(n_words(p.stripped) for p in intro)
    if n > 1000:
        return res("in.breve", desc, "AP", f"{n} palavras: introdução extensa para o formato 'breve'. Conteúdo (revisão, justificativa) deve ser avaliado pelo revisor.",
                   [note(intro[0], f"Introdução com {n} palavras: torne-a mais breve (revisão da literatura, justificativa e objetivo).")])
    return res("in.breve", desc, "-", f"{n} palavras. Revisão da literatura, justificativa e objetivo devem ser avaliados pelo revisor.")


def item_in_objetivo(ctx: Ctx):
    desc = "O objetivo é coerente com a proposta do estudo, idêntico ao apresentado no resumo, destacado no último parágrafo da introdução e é iniciado por verbo no infinitivo."
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
        return res("in.objetivo", desc, "NA", "Objetivo não identificado na Introdução (ex.: “O objetivo deste estudo foi analisar...” / “The aim of this study was to analyze...” / “El objetivo fue analizar...”)",
                   [note(intro[-1], "Destaque aqui o objetivo do estudo, iniciado por verbo no infinitivo.")])
    msgs, notes = [], []
    if not in_last:
        msgs.append(f"objetivo está em {ctx.where(para)}, não no último parágrafo")
        notes.append(note(para, "O objetivo deve ficar no último parágrafo da Introdução."))
    if not is_infinitive(verb):
        msgs.append(f"objetivo não inicia com verbo no infinitivo (encontrado '{verb}')")
        notes.append(note(para, f"O objetivo deve ser iniciado por verbo no infinitivo (encontrado “{verb}”)."))
    clause = find_objective(para.text)[2]
    seg, key = abstract_objective(ctx)
    cov = None
    if seg and clause:
        a, b = _tokens(clause), _tokens(find_objective(seg)[2] or seg)
        cov = len(a & b) / len(a) if a else 0
        if cov < 0.7:
            msgs.append(f"objetivo difere do apresentado no {key} ({cov:.0%} das palavras-chave em comum)")
            notes.append(note(para, f"O objetivo deve ser idêntico ao apresentado no {key} (apenas {cov:.0%} de correspondência)."))
    elif not seg:
        msgs.append("resumo no idioma do artigo não localizado para comparar o objetivo")
    if not msgs:
        return res("in.objetivo", desc, "A", f"Objetivo no último parágrafo, com verbo '{verb}'" + (f"; {cov:.0%} de correspondência com o {key}" if cov is not None else "") + ". Coerência com o estudo deve ser avaliada pelo revisor.")
    return res("in.objetivo", desc, "NA" if len(msgs) >= 2 else "AP", "; ".join(msgs), notes)


# ----------------------------- ÉTICA ----------------------------------------------------
ETHICS_KW = re.compile(r"[ée]tic|ethic|\bCEP\b|\bIRB\b|comit[êeé]|committee|review board|CAAE|resolu[çc][ãa]o|resolution|resoluci[oó]n|parecer|dictamen|opinion|"
                       r"protocolo|protocol|consentimento|consent|TCLE|CONEP|dispens|exempt|Helsinki|approv|aprova|aprobaci", re.IGNORECASE)
_COMMITTEE = r"comit[êeé]\s+de\s+[ée]tica|\bCEP\b|ethics?\s+committee|research\s+ethics|review\s+board|\bIRB\b|\bREC\b|institutional\s+ethics"
_APPROVAL = r"parecer|aprova|protocolo|CAAE|dictamen|aprobaci|approv|opinion|protocol|ethics?\s+approval|\bnumber\b"
WAIVER = re.compile(
    r"dados\s+(?:secund[aá]rios\s+)?(?:de\s+)?(?:dom[ií]nio\s+p[uú]blico|p[uú]blicos|agregados)|"
    r"dispens\w+\s+(?:de\s+|do\s+|da\s+)?(?:apreci|submiss|aprova|parecer|avalia|registro|n[uú]mero|CAAE|CEP|comit)|"
    r"(?:parecer|CAAE|CEP|protocolo|n[uú]mero|registro)[^.]{0,60}dispensad|"
    r"n[ãa]o\s+(?:foi\s+|ser[áa]\s+)?(?:necess|exig|envolv|requer|precis)\w+[^.]{0,70}(?:CEP|CAAE|comit[êe]|seres\s+humanos|apreci|parecer|aprova)|"
    r"sem\s+envolvimento\s+de\s+seres\s+humanos|n[ãa]o\s+envolve\s+seres\s+humanos|art(?:igo|\.)\s*1[º°]?[^.]{0,30}510|"
    # inglês
    r"(?:publicly\s+available|public[- ]domain|secondary|aggregated|anonymi[sz]ed|de-identified)\s+data|"
    r"(?:exempt(?:ed)?|waive[dr]?|waiver)\s+(?:from\s+)?(?:of\s+)?(?:the\s+)?(?:ethic\w*\s+)?(?:review|approval|evaluation|committee|CAAE|number)|"
    r"(?:did\s+not|does\s+not|not)\s+(?:require|need|involve|required)\b[^.]{0,70}(?:ethic\w*|committee|approval|human\s+subjects|IRB|CAAE)|"
    r"(?:ethic\w*|approval|committee|CAAE)[^.]{0,60}(?:was|were|is|are)\s+(?:not\s+required|waived|exempt)|"
    # espanhol
    r"datos\s+(?:secundarios\s+)?(?:de\s+dominio\s+p[uú]blico|p[uú]blicos|agregados)|exento\s+de\s+(?:revisi[oó]n|aprobaci[oó]n)|"
    r"no\s+(?:requiri[oó]|requiere|necesit[oó])[^.]{0,70}(?:comit[eé]|aprobaci[oó]n|[eé]tic)", re.IGNORECASE)
_MONTHS = (r"(?:jan(?:uary|eiro)?|feb(?:ruary|ruary)?|fev(?:ereiro)?|mar(?:ch|[çc]o|zo)?|apr(?:il)?|abr(?:il)?|may|mai(?:o)?|jun(?:e|ho|io)?|jul(?:y|ho|io)?|"
           r"aug(?:ust)?|ago(?:sto)?|sep(?:tember)?|set(?:embro)?|sept(?:iembre)?|oct(?:ober)?|out(?:ubro)?|nov(?:ember|embro|iembre)?|dec(?:ember)?|dez(?:embro)?|"
           r"ene(?:ro)?|dic(?:iembre)?)\.?")
DATE = re.compile(rf"\b\d{{1,2}}[/.\-]\d{{1,2}}[/.\-]\d{{2,4}}\b|\b\d{{1,2}}\s+(?:de\s+)?{_MONTHS}\s+(?:de\s+)?\d{{4}}\b|\b{_MONTHS}\s+\d{{1,2}},?\s+\d{{4}}\b|"
                  rf"\b(?:em|data|on|in|date[d]?|approved\s+(?:on|in)|aprobado\s+(?:el|en))\s*(?:de\s+)?(?:{_MONTHS}\s+(?:de\s+)?)?\d{{4}}\b", re.IGNORECASE)


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
            elif re.search(r"n[uú]mero|number|date|data\b|fecha|protocolo|protocol|registro", s, re.I) and not re.search(r"seres\s+humanos|human|dom[ií]nio|domain|p[uú]blic|apreci|review", s, re.I):
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


def _w(ctx):  # frase de dispensa para citar no comentário
    t = " ".join(p.text for p in _methods(ctx))
    if not WAIVER.search(t):
        return ""
    sent = next((x for x in _sentences(t) if WAIVER.search(x)), "")
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
    desc = "Para estudos que envolvem seres humanos, indica no último parágrafo do método o parecer CEP (exceto se o manuscrito declarar a dispensa)"
    et, M = _ethics_text(ctx)
    if not M:
        return res("et.parecer", desc, "-", "Métodos não encontrados")
    if re.search(_COMMITTEE, et, re.IGNORECASE) and re.search(_APPROVAL, et, re.IGNORECASE):
        return res("et.parecer", desc, "A", "Parecer/aprovação do comitê de ética indicado")
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
    found = sorted(set(re.findall(r"\b(466|510|580)\b", txt))) if re.search(r"Resolu|Resolution", txt, re.IGNORECASE) else []
    if found:
        return res("et.resolucoes", desc, "A", "Resolução(ões) citada(s): " + ", ".join(found))
    if waived(ctx):
        return res("et.resolucoes", desc, "NSA", f"Estudo com dispensa de apreciação ética: {_w(ctx)}")
    return res("et.resolucoes", desc, "NA", "Nenhuma das Resoluções 466/2012, 510/2016 ou 580/2018 foi citada em Métodos",
               [note(M[-1], "Informe que a pesquisa seguiu as Resoluções 466/2012, 510/2016 ou 580/2018 do Ministério da Saúde.")])


def item_et_protocolo(ctx: Ctx):
    desc = "Apresenta o número do protocolo de aprovação do projeto de pesquisa e data de aprovação do projeto de pesquisa no Comitê de Ética em Pesquisa (exceto se o manuscrito declarar a dispensa)"
    et, M = _ethics_text(ctx)
    if not M:
        return res("et.protocolo", desc, "-", "Métodos não encontrados")
    if not et and waived(ctx, "protocolo"):
        return res("et.protocolo", desc, "NSA", f"Estudo com dispensa de apreciação ética: {_w(ctx)}")
    proto = re.search(r"(?:parecer|protocolo|protocol|opinion|dictamen|aprova\w+|approv\w+)[^.;]{0,40}?\d[\d.\-/]{3,}|CAAE[^.;]{0,15}\d{8}", et, re.IGNORECASE)
    date = DATE.search(re.sub(r"CAAE[\s:nº°.]*[\d.]+", "", et))
    if proto and date:
        return res("et.protocolo", desc, "A", "Número do protocolo/parecer e data de aprovação encontrados")
    if waived(ctx, "protocolo"):
        return res("et.protocolo", desc, "NSA", f"O manuscrito declara dispensa do número/data do parecer: {_w(ctx)}")
    miss = "a data de aprovação" if proto else ("o número do protocolo/parecer" if date else "o número do protocolo/parecer e a data de aprovação")
    return res("et.protocolo", desc, "AP" if (proto or date) else "NA", f"Falta {miss} (último parágrafo de Métodos)", [note(M[-1], f"Informe {miss} no CEP.")])


def item_et_caae(ctx: Ctx):
    desc = "O número do CAAE (Certificado de Apresentação de Apreciação Ética) foi adicionado nos Métodos (exceto se o manuscrito declarar a dispensa)"
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
        return res("et.caae", desc, "AP", "CAAE mencionado, mas fora do formato 00000000.0.0000.0000", [note(p, "Informe o CAAE no formato 00000000.0.0000.0000.")])
    return res("et.caae", desc, "NA", "CAAE não encontrado em Métodos (nem declaração de dispensa)",
               [note(M[-1], "Informe o número do CAAE (00000000.0.0000.0000) ou declare a dispensa de apreciação ética.")])


# ----------------------------- RESULTADOS / DISCUSSÃO --------------------------------------------
def item_rs_sequencia(ctx: Ctx):
    return res("rs.sequencia", "Os resultados estão descritos em sequência lógica.", "-", "Avaliação do revisor (sequência lógica dos resultados)")


def item_di_literatura(ctx: Ctx):
    return res("di.literatura", "Apresenta os resultados comparados com os resultados da literatura e adequadamente discutidos.", "-", "Avaliação do revisor (comparação com a literatura)")


LIM = re.compile(r"limita[çc]|limitation|limitaci[oó]n|barreira|dificuldade|vi[eé]s\b|bias|sesgo|restri[çc][ãa]o|weakness|shortcoming|constraint|caveat", re.IGNORECASE)
MIT = re.compile(r"mitig|minimiz|minimi[sz]|reduz|reduc|control|sugere-se|recomenda-se|estudos\s+futuros|pesquisas\s+futuras|valida|ampliar|futuros?\s+estudos|"
                 r"future\s+(?:studies|research|work)|further\s+(?:studies|research)|should\s+be|recommend|adjust|sensitivity|futuras?\s+investigaciones|futuros\s+estudios", re.IGNORECASE)


def item_di_limitacoes(ctx: Ctx):
    desc = "Indica no penúltimo parágrafo as limitações do estudo e formas de mitigação"
    D = ctx.sections.get("DISCUSSION")
    if len(D) < 2:
        return res("di.limitacoes", desc, "-" if not D else "NA", "Discussão não encontrada ou com menos de dois parágrafos")
    sep = ctx.sections.has("CONCLUSION")
    # com Conclusão em seção separada, o último parágrafo da Discussão passará a ser o penúltimo quando a conclusão for incorporada a ele
    target = D[-1] if sep else D[-2]
    where_t = "último parágrafo da Discussão (que será o penúltimo ao incorporar a Conclusão)" if sep else "penúltimo parágrafo"
    if LIM.search(target.text):
        if MIT.search(target.text):
            return res("di.limitacoes", desc, "A", f"Limitações e formas de mitigação no {where_t}")
        return res("di.limitacoes", desc, "AP", f"Limitações no {where_t} ({ctx.where(target)}), sem formas de mitigação",
                   [note(target, "Inclua as formas de mitigação das limitações do estudo.")])
    where = [i for i, p in enumerate(D) if LIM.search(p.text)]
    if where:
        return res("di.limitacoes", desc, "AP", f"Limitações citadas em {ctx.where(D[where[0]])}, mas devem estar no {where_t} ({ctx.where(target)})",
                   [note(D[where[0]], "As limitações do estudo e as formas de mitigação devem estar no penúltimo parágrafo da Discussão (com a conclusão incorporada ao último).")])
    return res("di.limitacoes", desc, "NA", f"Limitações do estudo não encontradas na Discussão: acrescente-as no {where_t} ({ctx.where(target)})",
               [note(target, "Descreva aqui as limitações do estudo e as formas de mitigação (penúltimo parágrafo da Discussão).")])
