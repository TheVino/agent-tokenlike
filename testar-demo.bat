@echo off
rem Modo demo: tokens falsos para ver o pet comer e evoluir em ~1 minuto.
rem O progresso do demo fica separado do progresso real.
cd /d "%~dp0"
python "%~dp0tokenlike.py" --demo
pause
