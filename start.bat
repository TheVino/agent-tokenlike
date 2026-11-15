@echo off
rem Opens Agent Tokenlike without a terminal window.
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0tokenlike.py" %*
) else (
    start "" pyw "%~dp0tokenlike.py" %*
)
