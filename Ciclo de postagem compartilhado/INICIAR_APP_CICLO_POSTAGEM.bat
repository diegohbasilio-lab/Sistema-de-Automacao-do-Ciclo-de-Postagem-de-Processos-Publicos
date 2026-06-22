@echo off
cd /d "%~dp0"

set "PYTHONW_LOCAL=%~dp0robo_sped\venv\Scripts\pythonw.exe"
set "PYTHON_LOCAL=%~dp0robo_sped\venv\Scripts\python.exe"

if exist "%PYTHONW_LOCAL%" (
    start "" "%PYTHONW_LOCAL%" "%~dp0app_ciclo_postagem.py"
) else if exist "%PYTHON_LOCAL%" (
    start "" "%PYTHON_LOCAL%" "%~dp0app_ciclo_postagem.py"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        start "" py "%~dp0app_ciclo_postagem.py"
    ) else (
        start "" python "%~dp0app_ciclo_postagem.py"
    )
)
