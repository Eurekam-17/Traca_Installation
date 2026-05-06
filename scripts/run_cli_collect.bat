@echo off
REM Test la collecte system_info en CLI (n'aboutira pas sur Windows :
REM dmidecode/sysfs sont des outils Linux. Utile pour valider les imports).
setlocal
cd /d "%~dp0\.."
chcp 65001 > nul
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
python -m system_info.cli %*
endlocal
