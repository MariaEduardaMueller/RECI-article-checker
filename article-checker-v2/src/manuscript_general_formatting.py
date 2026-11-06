"""FORMATAÇÃO GERAL DO MANUSCRITO."""
import re
from collections import Counter

from common import Ctx, fmt_list, is_one_half, is_simple, is_times, n_words, note, res, sizes_ok
from structure import BODY_KEYS, SECTION_PT

CAPTION_RX = re.compile(r"^\s*(Tabela|Quadro|Figura|Gr[aá]fico)\s*\d+", re.IGNORECASE)
GENERIC_PROPS = {"python-docx", "openpyxl"}
HOW_PROPS = "Word: Arquivo > Informações > Verificar Problemas > Inspecionar Documento > Propriedades do Documento."


def item_fg_autoria(ctx: Ctx):
    desc = "A identificação de autoria do trabalho foi removida do arquivo e da opção Propriedades no Word"
    labels = {"author": "Autor", "last_modified_by": "Última modificação por", "company": "Empresa", "manager": "Gerente"}
    found = {labels[k]: v for k, v in ctx.doc.props.items() if k in labels and v and v.strip() and v.strip().lower() not in GENERIC_PROPS}
    if found:
        return res("fg.autoria", desc, "NA", "Propriedades do arquivo com identificação: " + "; ".join(f"{k}='{v}'" for k, v in found.items()) + ". " + HOW_PROPS,
                   [note(None, "Propriedades do arquivo contêm identificação de autoria (" + "; ".join(f"{k}='{v}'" for k, v in found.items()) + "). " + HOW_PROPS)])
    return res("fg.autoria", desc, "A", "Nenhuma identificação de autoria nas propriedades do arquivo")


def item_fg_formato(ctx: Ctx):
    desc = "Está em formato Microsoft Word, digitado em .doc, até 2MB"
    mb = ctx.doc.size_bytes / (1024 * 1024)
    if mb > 2:
        return res("fg.formato", desc, "NA", f"Arquivo com {mb:.2f} MB (máximo 2 MB): reduza o tamanho (compactar imagens).")
    return res("fg.formato", desc, "A", f"Arquivo Word (.docx) com {mb:.2f} MB")


def _dominant(p):
    c = Counter()
    for r in p.visible_runs():
        if r.size and not r.superscript:
            c[round(r.size, 1)] += len(r.text)
    return c.most_common(1)[0][0] if c else None


def _body(ctx):
    S = ctx.sections
    return [p for k in BODY_KEYS + ("ACKNOWLEDGMENTS",) for p in S.get(k)
            if not CAPTION_RX.match(p.stripped) and not p.n_images]


def _examples(ctx, paras, text, n=3):
    return [note(p, text) for p in paras[:n]]


def item_fg_fonte(ctx: Ctx):
    desc = "Redigido na ortografia oficial, fonte Times New Roman 12, com espaçamento 1,5, sem espaçamento entre parágrafos"
    S = ctx.sections
    body = _body(ctx)
    scope = body + [p for k in ("RESUMO", "ABSTRACT", "RESUMEN", "REFERENCES") for p in S.get(k)]
    if not body:
        return res("fg.fonte", desc, "-", "Corpo do texto não identificado (seções Introdução a Discussão).")
    groups: dict[str, list] = {}
    for p in scope:
        fonts = p.fonts()
        if fonts and not all(is_times(f) for f in fonts):
            groups.setdefault(f"fonte {'/'.join(sorted(fonts))} (esperado Times New Roman)", []).append(p)
        sizes = p.sizes() - {r.size for r in p.runs if r.superscript}
        if sizes and not sizes_ok(sizes, 12):
            groups.setdefault(f"tamanho {'/'.join(f'{s:g}' for s in sorted(sizes))}pt (esperado 12pt)", []).append(p)
    for p in body:
        if is_one_half(p) is False:
            groups.setdefault(f"espaçamento entre linhas {p.line_spacing:g} (esperado 1,5)", []).append(p)
        if (p.space_after or 0) > 0.5 or (p.space_before or 0) > 1.5:
            groups.setdefault("espaçamento entre parágrafos (esperado nenhum)", []).append(p)
    total = len(scope)
    bad_total = sum(len(v) for v in groups.values())
    if not groups:
        return res("fg.fonte", desc, "A", f"{total} parágrafos conferidos: fonte, tamanho e espaçamento corretos. Ortografia oficial não é verificada automaticamente.")
    msg, notes = [], []
    for k, ps in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:4]:
        msg.append(f"{k}: {len(ps)} parágrafo(s), a partir de {ctx.where(ps[0], True)}")
        notes += _examples(ctx, ps, f"{k}. Ajuste este parágrafo (e os demais na mesma situação: {len(ps)} no total).", 2)
    return res("fg.fonte", desc, "AP" if bad_total <= 0.1 * total else "NA", "; ".join(msg) + ". Ortografia oficial não é verificada automaticamente.", notes)


def item_fg_simples(ctx: Ctx):
    desc = "Títulos do manuscrito, Resumos, Figuras, Tabelas e Referências devem estar com espaçamento simples"
    from titles import title_lines
    S = ctx.sections
    groups = {
        "títulos": [t.para for t in title_lines(ctx)],
        "resumos/descritores": [p for k in ("RESUMO", "ABSTRACT", "RESUMEN") for p in S.get(k)],
        "legendas de figuras/tabelas": [p for p in ctx.doc.body if CAPTION_RX.match(p.stripped)],
        "tabelas": [p for p in ctx.doc.paragraphs if p.in_table and p.stripped],
        "referências": S.get("REFERENCES"),
    }
    msgs, notes = [], []
    for name, ps in groups.items():
        bad = [p for p in ps if is_simple(p) is False]
        if bad:
            msgs.append(f"{name}: espaçamento {bad[0].line_spacing:g} em {len(bad)}/{len(ps)} parágrafo(s) (ex.: {ctx.where(bad[0])})")
            notes += _examples(ctx, bad, f"{name.capitalize()} devem ter espaçamento simples (atual: {bad[0].line_spacing:g}).", 2)
    return res("fg.simples", desc, "NA" if msgs else "A", "; ".join(msgs) if msgs else "Espaçamento simples em títulos, resumos, legendas, tabelas e referências", notes)


GENERA = ("Escherichia|Klebsiella|Staphylococcus|Streptococcus|Acinetobacter|Pseudomonas|Candida|Aedes|Anopheles|Plasmodium|"
          "Trypanosoma|Leishmania|Mycobacterium|Salmonella|Enterococcus|Helicobacter|Homo|Mus|Rattus|Drosophila|"
          "Saccharomyces|Bacillus|Clostridium|Lactobacillus|Cryptococcus|Aspergillus|Toxoplasma|Schistosoma|"
          "Biomphalaria|Taenia|Ascaris|Giardia|Vibrio|Neisseria|Treponema|Chlamydia|Legionella|Haemophilus")
SCIENTIFIC = re.compile(rf"\b(?:(?:{GENERA})\s+[a-z]{{3,}}|[A-Z][a-z]+(?:coccus|bacter|bacterium|monas|ella|ichia|illus|myces)\s+[a-z]{{3,}}|"
                        r"[A-Z]\.\s?(?:coli|aureus|pneumoniae|aegypti|albicans|baumannii|aeruginosa|pyogenes|typhi|cruzi|mansoni|pylori))\b")
FOREIGN = re.compile(r"\b(in vitro|in vivo|in situ|ex vivo|sensu|per se|a priori|a posteriori|ad hoc|versus|per capita|"
                     r"fake news|feedback|odds ratio|machine learning|big data|bullying|burnout|follow-up|screening|"
                     r"stricto sensu|lato sensu|status quo|et al|software|SPSS|Stata|Excel|Epi Info|RStudio|Joinpoint|Python)\b", re.IGNORECASE)


def item_fg_italico(ctx: Ctx):
    desc = "Itálico para palavras de idioma diferente do manuscrito (ex.: nomes científicos, softwares)"
    wrong, total, notes = [], 0, []
    for k in BODY_KEYS:
        for p in ctx.sections.get(k):
            for rx in (SCIENTIFIC, FOREIGN):
                for m in rx.finditer(p.text):
                    total += 1
                    runs = p.runs_in(m.start(), m.end())
                    if runs and not all(r.italic for r in runs):
                        wrong.append(f"{m.group(0)} ({ctx.where(p)})")
                        notes.append(note(p, f"Coloque “{m.group(0)}” em itálico (termo de outro idioma/nome científico/software).", m.start(), m.end()))
    if total == 0:
        return res("fg.italico", desc, "A", "Nenhum nome científico/termo estrangeiro detectado automaticamente (verificação por lista; confirme manualmente).")
    if wrong:
        return res("fg.italico", desc, "NA", "Sem itálico: " + fmt_list(wrong, 5), notes[:15])
    return res("fg.italico", desc, "A", f"{total} termo(s) estrangeiro(s)/científico(s) em itálico")


def item_fg_secoes(ctx: Ctx):
    desc = "Seções: Introdução, Métodos, Resultados, Discussão, Agradecimentos (opcional), Referências e Contribuição dos autores (após as Referências)"
    S = ctx.sections
    required = ["INTRODUCTION", "METHODS", "RESULTS", "DISCUSSION", "REFERENCES"]
    msgs, notes, grave = [], [], False
    missing = [SECTION_PT[k] for k in required if not (S.has(k) and S.words(k) > 0)]
    if missing:
        grave = True
        msgs.append(f"Seções não encontradas: {', '.join(missing)}")
        notes.append(note(None, f"Seção(ões) obrigatória(s) ausente(s): {', '.join(missing)}."))
    order = [k for k in S.order if k in required + ["ACKNOWLEDGMENTS", "CONTRIBUTIONS", "CONCLUSION"]]
    expected = [k for k in ["INTRODUCTION", "METHODS", "RESULTS", "DISCUSSION", "ACKNOWLEDGMENTS", "REFERENCES", "CONTRIBUTIONS"] if k in order]
    if S.has("CONCLUSION"):
        h = S.heading["CONCLUSION"]
        msgs.append(f"seção “{h.stripped}” deve ser removida ({ctx.where(h)}); a conclusão vai no último parágrafo da Discussão")
        notes.append(note(h, "Remova a seção de Conclusão (artigo original): incorpore-a ao último parágrafo da Discussão."))
    if [k for k in order if k != "CONCLUSION"] != expected:
        msgs.append("ordem das seções fora do esperado: " + " > ".join(SECTION_PT.get(k, "Contribuição dos autores") for k in order))
    if not S.has("CONTRIBUTIONS") or S.words("CONTRIBUTIONS") == 0:
        grave = grave or False
        msgs.append("falta a seção “Contribuição dos autores” após as Referências")
        last = S.get("REFERENCES")
        notes.append(note(last[-1] if last else None, "Inclua, após as Referências, a seção “CONTRIBUIÇÃO DOS AUTORES” descrevendo a contribuição de cada autor."))
    elif "REFERENCES" in order and "CONTRIBUTIONS" in order and order.index("CONTRIBUTIONS") < order.index("REFERENCES"):
        h = S.heading["CONTRIBUTIONS"]
        msgs.append("a seção Contribuição dos autores deve vir depois das Referências")
        notes.append(note(h, "Mova esta seção para depois das Referências."))
    if not msgs:
        return res("fg.secoes", desc, "A", "Seções encontradas na ordem correta, incluindo Contribuição dos autores após as Referências")
    return res("fg.secoes", desc, "NA" if grave or len(msgs) >= 3 else "AP", "; ".join(msgs), notes)


def item_fg_esquerda(ctx: Ctx):
    desc = "Todos os títulos estão alinhados à margem esquerda"
    S = ctx.sections
    if not any(k in S.heading for k in BODY_KEYS):
        return res("fg.esquerda", desc, "-", "Seções não identificadas.")
    bad, notes = [], []
    for k, p in S.heading.items():
        if k in ("INTRODUCTION", "METHODS", "RESULTS", "DISCUSSION", "ACKNOWLEDGMENTS", "REFERENCES", "CONTRIBUTIONS") and p.align in ("center", "right", "justify"):
            bad.append(f"{p.stripped} ({p.align})")
            notes.append(note(p, "Título de seção deve estar alinhado à margem esquerda."))
    return res("fg.esquerda", desc, "NA" if bad else "A", ("Fora da margem esquerda: " + ", ".join(bad)) if bad else "Títulos das seções alinhados à esquerda", notes)


def item_fg_espac_secoes(ctx: Ctx):
    desc = "Todos os títulos das seções estão com espaçamento 1,5"
    heads = [(k, p) for k, p in ctx.sections.heading.items() if k in BODY_KEYS + ("ACKNOWLEDGMENTS", "REFERENCES", "CONTRIBUTIONS")]
    if not heads:
        return res("fg.espac_secoes", desc, "-", "Seções não identificadas.")
    bad = [(k, p) for k, p in heads if is_one_half(p) is False]
    notes = [note(p, f"Título de seção com espaçamento {p.line_spacing:g}; use 1,5.") for _, p in bad]
    return res("fg.espac_secoes", desc, "NA" if bad else "A",
               ("Espaçamento ≠ 1,5 em: " + ", ".join(f"{p.stripped} ({p.line_spacing:g})" for _, p in bad)) if bad else "Títulos das seções com espaçamento 1,5", notes)


def item_fg_recuo(ctx: Ctx):
    desc = "Todos os parágrafos devem estar com recuo de 1,5 (cm, na primeira linha)"
    body = [p for p in _body(ctx) if not (p.all_bold() and n_words(p.stripped) < 12) and n_words(p.stripped) >= 5]
    if not body:
        return res("fg.recuo", desc, "-", "Corpo do texto não identificado")
    bad = [p for p in body if p.first_indent is None or abs(p.first_indent - 1.5) > 0.15]
    if not bad:
        return res("fg.recuo", desc, "A", f"{len(body)} parágrafos com recuo de 1,5 cm")
    got = Counter(f"{(p.first_indent or 0):.1f} cm" for p in bad).most_common(2)
    notes = [note(p, f"Recuo da primeira linha de {(p.first_indent or 0):.1f} cm; use 1,5 cm (Parágrafo > Recuo > Especial: Primeira linha, 1,5 cm).") for p in bad[:3]]
    return res("fg.recuo", desc, "AP" if len(bad) <= 0.1 * len(body) else "NA",
               f"{len(bad)}/{len(body)} parágrafos sem recuo de 1,5 cm (encontrado: {', '.join(f'{v} ×{n}' for v, n in got)}), a partir de {ctx.where(bad[0], True)}", notes)


def item_fg_palavras(ctx: Ctx):
    desc = "Apresenta no máximo 4.000 palavras (da Introdução à Discussão)"
    S = ctx.sections
    counts = {k: sum(n_words(p.stripped) for p in S.get(k) if not CAPTION_RX.match(p.stripped)) for k in BODY_KEYS}
    total = sum(counts.values())
    detail = f"Total de palavras ({total}): " + ", ".join(f"{SECTION_PT[k]} ({v})" for k, v in counts.items())
    if total == 0:
        return res("fg.palavras", desc, "-", "Não foi possível contar: seções não identificadas.")
    if total > 4000:
        return res("fg.palavras", desc, "NA", detail + f" — reduzir {total - 4000} palavras", [note(S.heading.get("INTRODUCTION"), f"O texto (Introdução a Discussão) tem {total} palavras; o limite é 4.000.")])
    return res("fg.palavras", desc, "A", detail)
