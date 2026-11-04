"""FORMATAÇÃO GERAL DO MANUSCRITO — itens 12, 13, 14, 16, 18, 110 e 111."""
import re
from collections import Counter

from common import Ctx, fmt_list, is_one_half, is_simple, is_times, n_words, res, sizes_ok
from structure import BODY_KEYS, SECTION_PT

CAPTION_RX = re.compile(r"^\s*(Tabela|Quadro|Figura|Gr[aá]fico)\s*\d+", re.IGNORECASE)
GENERIC_PROPS = {"python-docx", "openpyxl"}


def item_12(ctx: Ctx):
    desc = "A identificação de autoria do trabalho foi removida do arquivo e da opção Propriedades no Word"
    props = ctx.doc.props
    labels = {"author": "Autor", "last_modified_by": "Última modificação por", "company": "Empresa",
              "manager": "Gerente", "creator": "Criador"}
    found = {labels[k]: v for k, v in props.items() if k in labels and v and v.strip()
             and v.strip().lower() not in GENERIC_PROPS and not (ctx.doc.fmt == "pdf" and k == "creator")}
    if found:
        how = "Word: Arquivo > Informações > Verificar Problemas > Inspecionar Documento > Propriedades do Documento."
        return res(12, desc, "NA", "Propriedades com identificação: " + "; ".join(f"{k}='{v}'" for k, v in found.items()) + ". " + how)
    return res(12, desc, "A", "Nenhuma identificação de autoria nas propriedades do arquivo")


def item_13(ctx: Ctx):
    desc = "Está em formato Microsoft Word, digitado em .docx, até 2MB"
    d = ctx.doc
    mb = d.size_bytes / (1024 * 1024)
    probs = []
    if d.fmt != "docx":
        probs.append(f"arquivo em formato .{d.fmt} (a revista exige Word .docx)")
    if mb > 2:
        probs.append(f"tamanho {mb:.2f} MB (máximo 2 MB)")
    return res(13, desc, "NA" if probs else "A", "; ".join(probs) if probs else f"Arquivo .docx com {mb:.2f} MB")


def _scopes(ctx: Ctx):
    S = ctx.sections
    body = [p for k in BODY_KEYS + ("ACKNOWLEDGMENTS",) for p in S.get(k)
            if not CAPTION_RX.match(p.stripped) and not p.n_images]
    simple = [p for k in ("RESUMO", "ABSTRACT", "RESUMEN", "REFERENCES") for p in S.get(k)]
    if not ctx.doc.exact:      # PDF: rótulos de gráficos/tabelas viram parágrafos — ficam só os de tamanho dominante
        cnt = Counter()
        for p in body:
            d = _dominant(p)
            if d:
                cnt[d] += len(p.text)
        if cnt:
            g = cnt.most_common(1)[0][0]
            body = [p for p in body if (_dominant(p) or 0) and abs(_dominant(p) - g) <= 0.6]
            simple = [p for p in simple if (_dominant(p) or 0) and abs(_dominant(p) - g) <= 0.6]
    return body, simple


def _dominant(p):
    c = Counter()
    for r in p.visible_runs():
        if r.size and not r.superscript:
            c[round(r.size, 1)] += len(r.text)
    return c.most_common(1)[0][0] if c else None


def _body_sizes(p):
    return {r.size for r in p.visible_runs() if r.size and not r.superscript}


def item_14(ctx: Ctx):
    desc = ("Redigido na ortografia oficial, fonte Times New Roman 12, com espaçamento 1,5, sem espaçamento entre "
            "parágrafos (exceto: Resumo, Figuras, Tabelas e Referências – espaçamento simples)")
    exact = ctx.doc.exact
    body, simple = _scopes(ctx)
    if not body:
        return res(14, desc, "-", "Corpo do texto não identificado (seções Introdução a Discussão).")

    issues, examples = Counter(), {}

    def flag(key, p):
        issues[key] += 1
        examples.setdefault(key, p.stripped[:40])

    for p in body + simple:
        fonts = p.fonts()
        if fonts and not all(is_times(f) for f in fonts):
            flag(f"fonte {'/'.join(sorted(fonts))} (esperado Times New Roman)", p)
        sizes = _body_sizes(p) if exact else ({_dominant(p)} if _dominant(p) else set())
        if sizes and not sizes_ok(sizes, 12):
            flag(f"tamanho {'/'.join(f'{s:g}' for s in sorted(sizes))}pt (esperado 12pt)", p)
    for p in body:
        if is_one_half(p, exact) is False:
            flag(f"espaçamento entre linhas {p.line_spacing:g} (esperado 1,5)", p)
        if (p.space_after or 0) > 0.5 or (p.space_before or 0) > (1.5 if exact else 5.5):
            flag("espaçamento entre parágrafos (esperado nenhum)", p)
    for p in simple:
        if is_simple(p, exact) is False:
            flag(f"espaçamento entre linhas {p.line_spacing:g} em Resumo/Referências (esperado simples)", p)

    total = len(body) + len(simple)
    bad_total = sum(issues.values())
    note = " Ortografia oficial não é verificada automaticamente." + ("" if exact else " (PDF: espaçamento estimado)")
    if not issues:
        return res(14, desc, "A", f"{total} parágrafos conferidos: fonte, tamanho e espaçamento corretos.{note}")
    msg = "; ".join(f"{k}: {v} parágrafo(s) (ex.: “{examples[k]}…”)" for k, v in issues.most_common(4))
    status = "AP" if bad_total <= 0.1 * total else "NA"
    return res(14, desc, status, msg + "." + note)


def item_16(ctx: Ctx):
    desc = "Deve ser dividido nas seguintes seções: Introdução, Métodos, Resultados, Discussão, Agradecimentos (opcional) e Referências"
    S = ctx.sections
    required = ["INTRODUCTION", "METHODS", "RESULTS", "DISCUSSION", "REFERENCES"]
    missing = [SECTION_PT[k] for k in required if not (S.has(k) and (S.words(k) > 0))]
    if missing:
        return res(16, desc, "NA", f"Seções não encontradas: {', '.join(missing)}")
    order = [k for k in S.order if k in required]
    if order != required:
        return res(16, desc, "AP", "Seções presentes, mas fora da ordem esperada: " + " > ".join(SECTION_PT[k] for k in order))
    return res(16, desc, "A", "Seções encontradas: " + ", ".join(SECTION_PT[k] for k in required))


def item_18(ctx: Ctx):
    desc = "Apresenta no máximo 4.000 palavras (da Introdução à Discussão)"
    S = ctx.sections
    counts = {k: sum(n_words(p.stripped) for p in S.get(k) if not CAPTION_RX.match(p.stripped)) for k in BODY_KEYS}
    total = sum(counts.values())
    detail = f"Total de palavras ({total}): " + ", ".join(f"{SECTION_PT[k]} ({v})" for k, v in counts.items())
    if total == 0:
        return res(18, desc, "-", "Não foi possível contar: seções não identificadas.")
    return res(18, desc, "NA" if total > 4000 else "A", detail)


# --------------------------------------------------------------------------------------
GENERA = ("Escherichia|Klebsiella|Staphylococcus|Streptococcus|Acinetobacter|Pseudomonas|Candida|Aedes|Anopheles|Plasmodium|"
          "Trypanosoma|Leishmania|Mycobacterium|Salmonella|Enterococcus|Helicobacter|Homo|Mus|Rattus|Drosophila|"
          "Saccharomyces|Bacillus|Clostridium|Lactobacillus|Cryptococcus|Aspergillus|Toxoplasma|Schistosoma|"
          "Biomphalaria|Taenia|Ascaris|Giardia|Vibrio|Neisseria|Treponema|Chlamydia|Legionella|Haemophilus")
SCIENTIFIC = re.compile(rf"\b(?:(?:{GENERA})\s+[a-z]{{3,}}|[A-Z][a-z]+(?:coccus|bacter|bacterium|monas|ella|ichia|illus|myces)\s+[a-z]{{3,}}|"
                        r"[A-Z]\.\s?(?:coli|aureus|pneumoniae|aegypti|albicans|baumannii|aeruginosa|pyogenes|typhi|cruzi|mansoni|pylori))\b")
FOREIGN = re.compile(r"\b(in vitro|in vivo|in situ|ex vivo|sensu|per se|a priori|a posteriori|ad hoc|versus|per capita|"
                     r"fake news|feedback|odds ratio|machine learning|big data|bullying|burnout|follow-up|screening|"
                     r"stricto sensu|lato sensu|status quo|et al)\b", re.IGNORECASE)


def item_110(ctx: Ctx):
    desc = "Itálico para palavras de idioma diferente do manuscrito (ex.: nomes científicos)"
    S = ctx.sections
    paras = [p for k in BODY_KEYS for p in S.get(k)]
    wrong, total = [], 0
    for p in paras:
        t = p.text
        for rx in (SCIENTIFIC, FOREIGN):
            for m in rx.finditer(t):
                total += 1
                runs = p.runs_in(m.start(), m.end())
                if runs and not all(r.italic for r in runs):
                    wrong.append(m.group(0))
    if total == 0:
        return res(110, desc, "A", "Nenhum nome científico/expressão estrangeira detectado automaticamente (verificação heurística; confirme manualmente).")
    if wrong:
        return res(110, desc, "NA", f"Sem itálico: {fmt_list(sorted(set(wrong)), 6)}")
    return res(110, desc, "A", f"{total} termo(s) estrangeiro(s)/científico(s) em itálico")


def item_111(ctx: Ctx):
    desc = "Seções INTRODUÇÃO, MÉTODOS, RESULTADOS, DISCUSSÃO, AGRADECIMENTOS e REFERÊNCIAS alinhadas à margem esquerda"
    S = ctx.sections
    bad = []
    for k, p in S.heading.items():
        if k in ("INTRODUCTION", "METHODS", "RESULTS", "DISCUSSION", "ACKNOWLEDGMENTS", "REFERENCES"):
            if p.align in ("center", "right"):
                bad.append(f"{p.stripped} ({p.align})")
    if not any(k in S.heading for k in BODY_KEYS):
        return res(111, desc, "-", "Seções não identificadas.")
    return res(111, desc, "NA" if bad else "A", ("Fora da margem esquerda: " + ", ".join(bad)) if bad else "Títulos das seções alinhados à esquerda")
