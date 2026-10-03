@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0
echo Iniciando Analisador de Licitacoes...
"%~dp0venv\Scripts\python.exe" -m streamlit run "licitacoes\ui\app.py"
pause
