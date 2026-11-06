import sys, tempfile, shutil, uuid
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from common import DEFAULT_MODEL
from pipeline import find_template, run_pipeline
from viewer import render_article_html, render_checklist_html

st.set_page_config(page_title="RECI Checker", layout="wide")
st.image(str(HERE / "static" / "banner.jpg"), use_container_width=True)
st.title("Verificador de manuscritos")


@st.cache_data(ttl=30)
def ia_status():
    try:
        import ollama
        resp = ollama.list()
        models = resp.get("models", []) if isinstance(resp, dict) else getattr(resp, "models", [])
        nomes = [(m.get("model") or m.get("name")) if isinstance(m, dict) else getattr(m, "model", "") for m in models]
        return True, [n for n in nomes if n]
    except Exception:
        return False, []


ia_ok, modelos = ia_status()
if not find_template():
    st.warning("Modelo de checklist não encontrado.")

# ---------------- entrada
with st.sidebar:
    st.header("Opções")
    usar_ia = st.checkbox("Usar IA (Ollama)", value=ia_ok, disabled=not ia_ok)
    modelo = st.selectbox("Modelo", modelos or [DEFAULT_MODEL], disabled=not usar_ia)
    ortografia = st.checkbox("Verificar ortografia", value=True)
    ms_id = st.text_input("ID do manuscrito", max_chars=30)

manuscrito = st.file_uploader("Manuscrito (.docx)", type=["docx"])
folha = st.file_uploader("Folha de rosto (.docx) — opcional", type=["docx"])

if st.button("Analisar", type="primary", disabled=manuscrito is None):
    # limpa execução anterior
    old = st.session_state.pop("job", None)
    if old:
        shutil.rmtree(old["dir"], ignore_errors=True)

    d = Path(tempfile.mkdtemp(prefix="reci_"))
    (d / "manuscrito.docx").write_bytes(manuscrito.getbuffer())
    if folha:
        (d / "folha.docx").write_bytes(folha.getbuffer())

    barra = st.progress(0.0)
    with st.status("Analisando…", expanded=True) as stt:
        def progress(msg, pct):
            barra.progress(min(max(pct / 100, 0), 1.0))
            stt.update(label=msg)

        try:
            r = run_pipeline(d / "manuscrito.docx", d,
                             cover=(d / "folha.docx") if folha else None,
                             use_llm=usar_ia, model=modelo, spelling=ortografia,
                             manuscript_id=ms_id.strip(), progress=progress)
            st.session_state["job"] = {"dir": d, "r": r, "stem": Path(manuscrito.name).stem}
            stt.update(label="Concluído", state="complete")
        except Exception as e:
            stt.update(label=f"Erro: {type(e).__name__}: {e}", state="error")
            shutil.rmtree(d, ignore_errors=True)

# ---------------- resultado
job = st.session_state.get("job")
if job:
    d, r, stem = job["dir"], job["r"], job["stem"]
    st.success(f"Título: {r['titulo']}")
    st.json(r["resumo"], expanded=False)
    for a in r["warnings"]:
        st.warning(a)

    c1, c2 = st.columns(2)
    docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if (d / "checklist.docx").exists():
        c1.download_button("⬇ Checklist (.docx)", (d / "checklist.docx").read_bytes(),
                           f"{stem}_checklist.docx", docx_mime)
    if (d / "comentado.docx").exists():
        c2.download_button("⬇ Artigo comentado (.docx)", (d / "comentado.docx").read_bytes(),
                           f"{stem}_comentado.docx", docx_mime)

    tab1, tab2 = st.tabs(["Checklist preenchido", "Artigo com comentários"])
    with tab1:
        if (d / "resultado.json").exists():
            components.html(render_checklist_html(d / "resultado.json"), height=800, scrolling=True)
    with tab2:
        if (d / "comentado.docx").exists():
            components.html(render_article_html(d / "comentado.docx"), height=800, scrolling=True)
