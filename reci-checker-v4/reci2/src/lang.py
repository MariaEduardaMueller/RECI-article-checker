"""Detecção simples de idioma (pt / en / es) sem dependências externas."""
import re

_PT = set("""de a o que e do da em um para é com não uma os no se na por mais as dos como mas foi ao ele das tem à seu sua
ou ser quando muito há nos já está eu também só pelo pela até isso ela entre era depois sem mesmo aos ter seus quem nas
me esse eles estão você tinha foram essa num nem suas meu às minha têm numa pelos elas havia seja qual será nós tenho lhe
deles essas esses pelas este fosse dele são associados associadas fatores idosos anos""".split())
_EN = set("""the of and to in a is that it for was on are as with his they at be this from have or by one had not but what all
were when we there can an your which their said if do will each about how up out them then she many some so these would
other into has more her two like him see time could no make than first been its who now people my made over did down only
way find use may among between factors associated older adults""".split())
_ES = set("""de la que el en y a los del se las por un para con no una su al lo como más pero sus le ya o este sí porque esta
entre cuando muy sin sobre también me hasta hay donde quien desde todo nos durante todos uno les ni contra otros ese eso
ante ellos e esto mí antes algunos qué unos yo otro otras otra él tanto esa estos mucho quienes nada muchos cual poco ella
estar estas algunas algo nosotros factores asociados ancianos años""".split())

_PT_MARK = {"com", "uma", "são", "não", "também", "muito", "anos", "mais", "entre", "idosos", "associados", "associadas", "fatores", "dos", "das"}
_ES_MARK = {"en", "un", "personas", "alimentaria", "alimentarias", "con", "una", "son", "también", "años", "más", "ancianos", "del", "los", "las", "asociados", "asociadas", "factores", "y"}
_EN_MARK = {"the", "with", "and", "for", "are", "was", "were", "been", "have", "has", "had", "their", "which", "this",
            "that", "from", "will", "among", "between", "factors", "associated", "older", "adults", "of", "in"}


def detect_language(text: str):
    low = text.lower()
    words = re.findall(r"\b\w+\b", low)
    if not words:
        return None
    pt = sum(w in _PT for w in words) + 2 * sum(w in _PT_MARK for w in words)
    en = sum(w in _EN for w in words) + 2 * sum(w in _EN_MARK for w in words)
    es = sum(w in _ES for w in words) + 2 * sum(w in _ES_MARK for w in words)
    if any(c in low for c in "ãõ"):
        pt += 5
    if any(c in low for c in "ñ¿¡"):
        es += 5
    if re.search(r"(ção|ções)\b", low):
        pt += 4
    if re.search(r"(ción|ciones)\b", low):
        es += 4
    if re.search(r"\w+(tion|ing|ity)\b", low):
        en += 2
    if pt == en == es == 0:
        return None
    best = max(pt, en, es)
    if pt == best and (pt - es) <= 2 and es >= pt - 2 and re.search(r"\b(con|una|son|más|ancianos|asociad\w+|factores)\b", low):
        return "spanish"
    if pt == best and re.search(r"[ãõç]|\b(não|são|uma|com|idosos|fatores)\b", low):
        return "portuguese"
    if best == pt and best != es and best != en:
        return "portuguese"
    if best == en and en > max(pt, es):
        return "english"
    if best == es and es > max(pt, en):
        return "spanish"
    # empates: desempata por caracteres típicos
    if en == best:
        return "english"
    return "portuguese" if pt >= es else "spanish"
