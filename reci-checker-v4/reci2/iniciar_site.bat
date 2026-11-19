@echo off
REM Inicia o site do reci-checker neste computador (http://127.0.0.1:5000)
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
python -m pip install -q -r requirements.txt
python web\app.py
pause
