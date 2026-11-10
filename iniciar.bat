@echo off
rem Abre o Agent Tokenlike sem janela de terminal.
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0tokenlike.py" %*
) else (
    start "" pyw "%~dp0tokenlike.py" %*
)
