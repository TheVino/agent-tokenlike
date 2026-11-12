@echo off
rem Modo demo: tokens falsos para ver o pet comer e evoluir em ~1 minuto.
rem O progresso do demo fica separado do progresso real. Abre sem janela de terminal.
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0tokenlike.py" --demo
) else (
    start "" pyw "%~dp0tokenlike.py" --demo
)
