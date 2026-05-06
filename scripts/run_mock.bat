@echo off
REM Lance la GUI en mode mock (aucun appel Odoo).
REM Usage : double-clic, ou depuis CMD : scripts\run_mock.bat
setlocal
cd /d "%~dp0\.."
chcp 65001 > nul
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
python src\main.py --mock %*
endlocal
