import json
from collections import Counter

from tabulate import tabulate

from catalog import display_text
from common import STATUS_LABEL


def flat(cat, sections):
    return [cat] + [r for _, rs in sections for r in rs]


def summary(cat, sections) -> Counter:
    return Counter(r["status"] for r in flat(cat, sections) if r["status"] != "SKIP")


def render_result(cat, sections):
    print("\n■ CATEGORIA DO MANUSCRITO: Artigo Original")
    print(tabulate([[cat["item"], cat["description"], cat["status"], cat["comments"]]], headers=["Item", "Descrição", "Status", "Comentários"],
                   maxcolwidths=[10, 50, 6, 70], tablefmt="simple_grid"))
    for name, rs in sections:
        print(f"\n■ {name}")
        data = [[r["item"], r["description"][:70], r["status"], r["comments"]] for r in rs]
        print(tabulate(data, headers=["Item", "Descrição", "Status", "Comentários"], maxcolwidths=[10, 50, 6, 70], tablefmt="simple_grid"))
    c = summary(cat, sections)
    print("\nResumo: " + " | ".join(f"{STATUS_LABEL[k]} ({k}): {c.get(k, 0)}" for k in ("A", "AP", "NA", "NSA", "-")))


def _item(ctx, r):
    return {"id": r["item"], "item": display_text(r["item"]) if r["item"] != "cat.refs" else "Mínimo de 10 e máximo de 25 referências no últimos 5 anos",
            "status": r["status"], "situacao": STATUS_LABEL.get(r["status"], r["status"]), "comentarios": r["comments"],
            "comentarios_no_texto": [{"paragrafo": n["para"] if n["para"] is None else n["para"] + 1, "onde": ctx.where(ctx.doc.paragraphs[n["para"]]) if n["para"] is not None else "documento",
                                      "trecho": (ctx.doc.paragraphs[n["para"]].text[n["start"]:n["end"]] if n["para"] is not None and n["start"] is not None else None),
                                      "comentario": n["text"]} for n in r.get("notes", [])]}


def export_json(ctx, cat, sections, path, meta=None):
    payload = {"meta": meta or {}, "resumo": dict(summary(cat, sections)), "categoria": _item(ctx, cat),
               "secoes": [{"nome": n, "itens": [_item(ctx, r) for r in rs]} for n, rs in sections]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
