"""pytest -q  — gera um manuscrito com defeitos propositais e confere o diagnóstico e os arquivos gerados."""
import json, subprocess, sys, zipfile, re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


@pytest.fixture(scope="session")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("s")
    subprocess.run([sys.executable, str(ROOT / "tests" / "make_samples.py"), str(d)], check=True)
    subprocess.run([sys.executable, str(SRC / "main.py"), str(d / "manuscrito.docx"), str(d / "folha_de_rosto.docx"),
                    "--saida", str(d / "out"), "--sem-llm"], check=True, capture_output=True)
    return d / "out"


def _items(out):
    j = json.loads((out / "manuscrito_checklist.json").read_text(encoding="utf-8"))
    return {i["id"]: i for s in j["secoes"] for i in s["itens"]}


@pytest.mark.parametrize("item,status", [
    ("fg.autoria", "NA"), ("fg.italico", "NA"), ("co.incorporada", "NA"), ("re.autores", "NA"),
    ("rf.vancouver", "NA"), ("rf.etal", "NA"), ("rf.doi", "AP"), ("tb.n_pct", "NA"), ("tb.total", "NA"),
    ("fi.centralizada", "NA"), ("et.caae", "NSA"), ("plag.plagio", "SKIP"), ("re.conciso", "A"),
])
def test_status(out, item, status):
    assert _items(out)[item]["status"] == status


def test_commented_copy_keeps_text(out, samples=None):
    import docx
    a = docx.Document(str(out.parent / "manuscrito.docx"))
    b = docx.Document(str(out / "manuscrito_comentado.docx"))
    assert [p.text for p in a.paragraphs] == [p.text for p in b.paragraphs]
    xml = zipfile.ZipFile(out / "manuscrito_comentado.docx").read("word/comments.xml").decode()
    assert len(re.findall("<w:comment ", xml)) > 10


def test_pdf_rejected(tmp_path):
    f = tmp_path / "a.pdf"; f.write_bytes(b"%PDF")
    r = subprocess.run([sys.executable, str(SRC / "main.py"), str(f)], capture_output=True, text=True)
    assert r.returncode != 0
