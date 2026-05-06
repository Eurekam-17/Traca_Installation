@echo off
REM Test la couche odoo_client en mode mock.
setlocal
cd /d "%~dp0\.."
chcp 65001 > nul
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
python -m odoo_client.cli --mock --next-serials %*
endlocal
