#!/usr/bin/env bash
# Inicia o site do reci-checker neste computador (http://127.0.0.1:5000)
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
python3 -m pip install -q -r requirements.txt
python3 web/app.py
