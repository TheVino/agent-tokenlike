@echo off
rem Demo mode: fake tokens to watch the pet eat and evolve in about a minute.
rem Demo progress is kept apart from the real progress. Opens without a terminal window.
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0tokenlike.py" --demo
) else (
    start "" pyw "%~dp0tokenlike.py" --demo
)
