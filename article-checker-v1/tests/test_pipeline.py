"""pytest tests/ — gera amostras (docx/pdf) e confere que erros injetados são detectados."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import make_samples                      # noqa: E402
from checklist import run_all            # noqa: E402
from common import Ctx                   # noqa: E402
from document_model import load_document  # noqa: E402


@pytest.fixture(scope="session")
def samples(tmp_path_factory):
    d = tmp_path_factory.mktemp("amostras")
    make_samples.build(d / "bom.docx", bad=False)
    make_samples.build(d / "ruim.docx", bad=True)
    make_samples.build_cover(d / "capa.docx")
    return d


def status(sections):
    return {r["item"]: r["status"] for _, rs in sections for r in rs}


def run(path, cover):
    return status(run_all(Ctx(load_document(path), load_document(cover), use_llm=False)))


def test_bom_docx_sem_reprovacoes(samples):
    s = run(samples / "bom.docx", samples / "capa.docx")
    assert [k for k, v in s.items() if v == "NA" and k not in (101, 102, 103, 104, 105)] == []


def test_ruim_docx_detecta_erros(samples):
    s = run(samples / "ruim.docx", samples / "capa.docx")
    for item in (12, 14, 20, 21, 33, 53, 54, 61, 69, 73, 125, 127, 128, 134, 136):
        assert s[item] == "NA", item
    assert s[119] == "AP"


def test_pdf_equivalente_ao_docx(samples):
    pytest.importorskip("pdfplumber")
    out = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(samples), str(samples / "bom.docx")],
                         capture_output=True, timeout=180)
    if not (samples / "bom.pdf").exists():
        pytest.skip("LibreOffice indisponível")
    s = run(samples / "bom.pdf", samples / "capa.docx")
    assert s[13] == "NA"                                  # PDF não é .docx
    assert [k for k, v in s.items() if v == "NA" and k not in (13, 101, 102, 103, 104, 105)] == []
