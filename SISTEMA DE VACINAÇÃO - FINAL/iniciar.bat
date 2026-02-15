@echo off
title Diagnostico NASST
echo ========================================
echo   INICIANDO SISTEMA DE VACINACAO
echo ========================================

:: Verifica se o Python existe
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] O Python nao foi encontrado instalado neste computador.
    echo Por favor, instale o Python em python.org e marque a opcao "Add Python to PATH".
    pause
    exit
)

:: Tenta rodar o sistema
echo [INFO] Tentando iniciar o Streamlit...
python -m streamlit run app.py

:: Se o sistema cair, ele nao fecha a tela
echo.
echo ========================================
echo [AVISO] O programa parou de rodar.
echo Verifique as mensagens de erro acima.
echo ========================================
pause