import json
from collections import Counter

from tabulate import tabulate

from common import STATUS_LABEL


def flat(sections):
    return [r for _, rs in sections for r in rs]


def summary(sections) -> Counter:
    return Counter(r["status"] for r in flat(sections))


def render_result(sections):
    for name, rs in sections:
        print(f"\n■ {name}")
        data = [[r["item"], r["description"], r["status"], r["comments"]] for r in rs]
        print(tabulate(data, headers=["Item", "Descrição", "Status", "Comentários"],
                       maxcolwidths=[6, 60, 6, 60], tablefmt="simple_grid"))
    c = summary(sections)
    print("\nResumo: " + " | ".join(f"{STATUS_LABEL[k]} ({k}): {c.get(k, 0)}" for k in ("A", "AP", "NA", "NSA", "-")))


def export_json(sections, path, meta=None):
    payload = {"meta": meta or {}, "summary": dict(summary(sections)),
               "sections": [{"name": n, "items": rs} for n, rs in sections]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
