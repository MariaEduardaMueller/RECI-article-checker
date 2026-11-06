"""Site local do reci-checker. Rode:  python web/app.py   e abra http://127.0.0.1:5000
Tudo é processado nesta máquina (nenhum arquivo sai dela). Os arquivos enviados são apagados após JOB_TTL_HORAS."""
import re
import shutil
import sys
import threading
import time
import uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from flask import Flask, Response, abort, jsonify, request, send_file, send_from_directory  # noqa: E402

from common import DEFAULT_MODEL  # noqa: E402
from pipeline import find_template, run_pipeline  # noqa: E402
from viewer import render_article_html, render_checklist_html  # noqa: E402

JOBS_DIR = HERE / "jobs"
JOB_TTL_HORAS = 6
MAX_UPLOAD_MB = 30
HOST, PORT = "127.0.0.1", 5000          # somente esta máquina; para a rede local use "0.0.0.0" (cuidado: manuscritos são sigilosos)

app = Flask(__name__, static_folder=str(HERE / "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()
POOL = ThreadPoolExecutor(max_workers=1)    # um manuscrito por vez (a IA ocupa a máquina)


def _safe_stem(name: str) -> str:
    stem = re.sub(r"[^\w\-. ]+", "_", Path(name).stem, flags=re.UNICODE).strip(" ._") or "manuscrito"
    return stem[:80]


def _cleanup():
    limite = time.time() - JOB_TTL_HORAS * 3600
    with LOCK:
        for jid in list(JOBS):
            if JOBS[jid]["criado"] < limite:
                shutil.rmtree(JOBS_DIR / jid, ignore_errors=True)
                JOBS.pop(jid, None)
    for d in JOBS_DIR.iterdir():            # sobras de execuções anteriores
        if d.is_dir() and d.name not in JOBS and d.stat().st_mtime < limite:
            shutil.rmtree(d, ignore_errors=True)


def _loop_limpeza():
    while True:
        time.sleep(1800)
        try:
            _cleanup()
        except Exception:
            pass


def _job_or_404(jid: str) -> dict:
    job = JOBS.get(jid)
    if job is None or not re.fullmatch(r"[0-9a-f]{32}", jid):
        abort(404)
    return job


def _executar(jid: str):
    job = JOBS[jid]
    d = JOBS_DIR / jid

    def progress(msg, pct):
        job["etapa"], job["pct"] = msg, pct

    job["status"] = "executando"
    try:
        r = run_pipeline(d / "manuscrito.docx", d, cover=(d / "folha.docx") if (d / "folha.docx").exists() else None,
                         use_llm=job["opcoes"]["usar_ia"], model=job["opcoes"]["modelo"], spelling=job["opcoes"]["ortografia"],
                         manuscript_id=job["opcoes"]["id"], progress=progress)
        job["resultado"] = {"resumo": r["resumo"], "avisos": r["warnings"], "ia": r["ia"], "titulo": r["titulo"],
                            "comentarios": r.get("comentarios", 0), "arquivos": [k for k in r["files"] if k != "json"]}
        job["status"] = "pronto"
    except Exception as e:  # noqa: BLE001
        job["status"], job["erro"] = "erro", f"{type(e).__name__}: {e}"


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/ia")
def ia_status():
    """A IA (Ollama) está acessível? Lista os modelos instalados."""
    try:
        import ollama  # type: ignore
        resp = ollama.list()
        models = resp.get("models", []) if isinstance(resp, dict) else getattr(resp, "models", [])
        nomes = [(m.get("model") or m.get("name")) if isinstance(m, dict) else getattr(m, "model", "") for m in models]
        return jsonify(disponivel=True, modelos=[n for n in nomes if n], padrao=DEFAULT_MODEL)
    except Exception as e:  # noqa: BLE001
        return jsonify(disponivel=False, modelos=[], padrao=DEFAULT_MODEL, erro=f"{type(e).__name__}")


@app.get("/api/config")
def config():
    return jsonify(modelo_checklist=bool(find_template()), max_mb=MAX_UPLOAD_MB, ttl_horas=JOB_TTL_HORAS)


@app.post("/api/analisar")
def analisar():
    f = request.files.get("manuscrito")
    if f is None or not f.filename:
        return jsonify(erro="Envie o manuscrito em Word (.docx)."), 400
    if not f.filename.lower().endswith(".docx"):
        return jsonify(erro="A RECI aceita somente manuscritos em Word (.docx)."), 400
    folha = request.files.get("folha")
    if folha and folha.filename and not folha.filename.lower().endswith(".docx"):
        return jsonify(erro="A folha de rosto também deve ser .docx."), 400
    _cleanup()
    jid = uuid.uuid4().hex
    d = JOBS_DIR / jid
    d.mkdir(parents=True)
    f.save(d / "manuscrito.docx")
    if folha and folha.filename:
        folha.save(d / "folha.docx")
    form = request.form
    JOBS[jid] = {
        "criado": time.time(), "status": "fila", "etapa": "Na fila", "pct": 0, "stem": _safe_stem(f.filename),
        "opcoes": {"usar_ia": form.get("usar_ia") == "1", "ortografia": form.get("ortografia") == "1",
                   "modelo": (form.get("modelo") or DEFAULT_MODEL).strip(), "id": (form.get("id") or "").strip()[:30]},
    }
    POOL.submit(_executar, jid)
    return jsonify(job=jid)


@app.get("/api/status/<jid>")
def status(jid):
    j = _job_or_404(jid)
    fila = sum(1 for x in JOBS.values() if x["status"] == "fila" and x["criado"] < j["criado"])
    return jsonify(status=j["status"], etapa=j["etapa"], pct=j["pct"], erro=j.get("erro"), resultado=j.get("resultado"),
                   na_frente=fila if j["status"] == "fila" else 0)


_ARQ = {"checklist": ("checklist.docx", "checklist"), "comentado": ("comentado.docx", "comentado")}


@app.get("/baixar/<jid>/<which>")
def baixar(jid, which):
    j = _job_or_404(jid)
    if which not in _ARQ or j["status"] != "pronto":
        abort(404)
    fn, suf = _ARQ[which]
    path = JOBS_DIR / jid / fn
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=f"{j['stem']}_{suf}.docx",
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.get("/ver/<jid>/<which>")
def ver(jid, which):
    j = _job_or_404(jid)
    if j["status"] != "pronto":
        abort(404)
    d = JOBS_DIR / jid
    if which == "checklist" and (d / "resultado.json").exists():
        return Response(render_checklist_html(d / "resultado.json", "Checklist preenchido"), mimetype="text/html")
    if which == "comentado" and (d / "comentado.docx").exists():
        return Response(render_article_html(d / "comentado.docx", "Artigo com comentários"), mimetype="text/html")
    abort(404)


@app.delete("/api/job/<jid>")
def apagar(jid):
    _job_or_404(jid)
    with LOCK:
        shutil.rmtree(JOBS_DIR / jid, ignore_errors=True)
        JOBS.pop(jid, None)
    return jsonify(ok=True)


if __name__ == "__main__":
    JOBS_DIR.mkdir(exist_ok=True)
    threading.Thread(target=_loop_limpeza, daemon=True).start()
    url = f"http://{HOST}:{PORT}"
    print(f"\nSite do reci-checker em {url}  (Ctrl+C para encerrar)\n")
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=HOST, port=PORT, threaded=True)
