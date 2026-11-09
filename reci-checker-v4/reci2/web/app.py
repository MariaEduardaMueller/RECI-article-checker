"""Site do reci-checker (Flask).
 * Local:  python web/app.py  ->  http://127.0.0.1:5000
 * Render: gunicorn --chdir web app:app ...  (veja render.yaml)
O usuário envia SOMENTE o manuscrito (.docx). Os arquivos são apagados após JOB_TTL_HORAS."""
import hmac
import os
import re
import shutil
import sys
import tempfile
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

from pipeline import find_template, run_pipeline  # noqa: E402
from viewer import render_article_html, render_checklist_html  # noqa: E402

HOSPEDADO = bool(os.environ.get("RENDER"))                       # o Render define RENDER=true
MODELO_IA = os.environ.get("MODELO_IA", "llama3.2:3b")           # só usado se houver um Ollama acessível (OLLAMA_HOST)
JOBS_DIR = Path(tempfile.gettempdir()) / "reci_jobs" if HOSPEDADO else HERE / "jobs"
JOB_TTL_HORAS = 2 if HOSPEDADO else 6
MAX_UPLOAD_MB = 10
MAX_FILA = 6                                                     # evita fila longa em máquina fraca
SITE_USER = os.environ.get("SITE_USER", "reci")
SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "")              # se definido, o site exige usuário/senha
HOST = "0.0.0.0" if HOSPEDADO else "127.0.0.1"
PORT = int(os.environ.get("PORT", 5000))

app = Flask(__name__, static_folder=str(HERE / "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()
POOL = ThreadPoolExecutor(max_workers=1)                         # um manuscrito por vez
JOBS_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------------------------ segurança
@app.before_request
def _auth():
    if not SITE_PASSWORD or request.path == "/healthz":
        return None
    a = request.authorization
    if a and hmac.compare_digest(a.username or "", SITE_USER) and hmac.compare_digest(a.password or "", SITE_PASSWORD):
        return None
    return Response("Acesso restrito.", 401, {"WWW-Authenticate": 'Basic realm="Verificador RECI"'})


@app.after_request
def _headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "no-referrer"
    if request.path.startswith(("/ver/", "/baixar/", "/api/")):
        resp.headers["Cache-Control"] = "no-store"
    return resp


# ------------------------------------------------------------------------------------ utilidades
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
    for d in JOBS_DIR.iterdir():
        if d.is_dir() and d.name not in JOBS and d.stat().st_mtime < limite:
            shutil.rmtree(d, ignore_errors=True)


def _loop_limpeza():
    while True:
        time.sleep(900)
        try:
            _cleanup()
        except Exception:
            pass


threading.Thread(target=_loop_limpeza, daemon=True).start()


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
        r = run_pipeline(d / "manuscrito.docx", d, cover=None, use_llm=job["opcoes"]["usar_ia"], model=MODELO_IA,
                         spelling=False, manuscript_id=job["opcoes"]["id"], progress=progress)
        job["resultado"] = {"resumo": r["resumo"], "avisos": r["warnings"], "ia": r["ia"], "titulo": r["titulo"],
                            "comentarios": r.get("comentarios", 0), "arquivos": [k for k in r["files"] if k != "json"]}
        job["status"] = "pronto"
    except Exception as e:  # noqa: BLE001
        job["status"], job["erro"] = "erro", f"{type(e).__name__}: {e}"


# ------------------------------------------------------------------------------------ rotas
@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/ia")
def ia_status():
    """Há um Ollama acessível com o modelo instalado? (No Render gratuito não há: o site usa só regras de código.)"""
    try:
        import ollama  # type: ignore
        resp = ollama.list()
        models = resp.get("models", []) if isinstance(resp, dict) else getattr(resp, "models", [])
        nomes = [(m.get("model") or m.get("name")) if isinstance(m, dict) else getattr(m, "model", "") for m in models]
        ok = any(n and n.startswith(MODELO_IA) for n in nomes)
        return jsonify(disponivel=ok, modelo=MODELO_IA, instalado=ok)
    except Exception:  # noqa: BLE001
        return jsonify(disponivel=False, modelo=MODELO_IA, instalado=False)


@app.get("/api/config")
def config():
    return jsonify(modelo_checklist=bool(find_template()), max_mb=MAX_UPLOAD_MB, ttl_horas=JOB_TTL_HORAS, hospedado=HOSPEDADO)


@app.post("/api/analisar")
def analisar():
    f = request.files.get("manuscrito")
    if f is None or not f.filename:
        return jsonify(erro="Envie o manuscrito em Word (.docx)."), 400
    if not f.filename.lower().endswith(".docx"):
        return jsonify(erro="A RECI aceita somente manuscritos em Word (.docx)."), 400
    _cleanup()
    if sum(1 for x in JOBS.values() if x["status"] in ("fila", "executando")) >= MAX_FILA:
        return jsonify(erro="O servidor está ocupado. Tente novamente em alguns minutos."), 503
    jid = uuid.uuid4().hex
    d = JOBS_DIR / jid
    d.mkdir(parents=True)
    f.save(d / "manuscrito.docx")
    form = request.form
    JOBS[jid] = {
        "criado": time.time(), "status": "fila", "etapa": "Na fila", "pct": 0, "stem": _safe_stem(f.filename),
        "opcoes": {"usar_ia": form.get("usar_ia") == "1", "id": (form.get("id") or "").strip()[:30]},   # IA desligada por padrão
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
    url = f"http://{HOST}:{PORT}"
    print(f"\nSite do reci-checker em {url}  (Ctrl+C para encerrar)\n")
    if not HOSPEDADO:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=HOST, port=PORT, threaded=True)
