@echo off
setlocal enabledelayedexpansion
echo ======================================================
echo    INSTALADOR DO ANALISADOR DE LICITacoes
echo ======================================================
echo.

cd /d "%~dp0"

:: Criar ambiente virtual
echo [+] Criando ambiente virtual Python...
python -m venv venv
call venv\Scripts\activate

echo [+] Instalando pacote em modo editavel...
pip install -e .

echo [+] Verificando Tesseract OCR...
tesseract --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Tesseract nao encontrado.
    echo     Por favor, baixe e instale em: https://github.com/UB-Mannheim/tesseract/wiki
) else (
    echo [OK] Tesseract instalado.
)

echo [+] Verificando Ollama...
curl http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Ollama nao detectado ou fechado.
    echo     Por favor, abra o Ollama antes de iniciar o programa.
) else (
    echo [OK] Ollama funcionando.
)

echo.
echo ======================================================
echo    INSTALACAO CONCLUIDA!
echo    Agora use o INICIAR.bat para abrir o programa.
echo ======================================================
pause
