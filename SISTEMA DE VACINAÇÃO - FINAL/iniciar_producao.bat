@echo off
title NASST Digital - PRODUÇÃO
color 0F

echo ==================================================
echo        NASST DIGITAL - MODO PRODUCAO
echo ==================================================
echo.
echo Verificando ambiente...

:: Verificar se Python existe
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale o Python em python.org
    pause
    exit
)

:: Verificar se .env existe
if not exist .env (
    echo [AVISO] Arquivo .env nao encontrado!
    echo Criando a partir do exemplo...
    copy .env.example .env
    echo.
    echo [IMPORTANTE] Edite o arquivo .env e defina:
    echo   - ADMIN_PASSWORD (senha forte do administrador)
    echo   - ENVIRONMENT=production
    echo.
    pause
    exit
)

:: Verificar se está em modo produção
findstr /C:"ENVIRONMENT=production" .env >nul
if %errorlevel% neq 0 (
    echo [AVISO] Modo PRODUCTION nao configurado!
    echo Editando .env e altere ENVIRONMENT para production
    pause
    exit
)

:: Verificar se senha admin foi alterada
findstr /C:"ADMIN_PASSWORD=admin123" .env >nul
if %errorlevel% equ 0 (
    echo [ERRO] Senha padrao do admin detectada!
    echo Altere a senha no arquivo .env antes de continuar.
    pause
    exit
)

echo Ambiente OK!
echo.
echo ==================================================
echo        INICIANDO SISTEMA EM MODO PRODUCAO
echo ==================================================
echo.

:: Executar em modo produção
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

echo.
echo ==================================================
echo [AVISO] O programa foi encerrado.
echo ==================================================
pause