@echo off
title NASST Digital - Testes do Sistema (Corrigido)
color 0F

:MENU
cls
echo ==================================================
echo        NASST DIGITAL - SISTEMA DE TESTES
echo        VERSAO CORRIGIDA
echo ==================================================
echo.
echo Versao: 1.0
echo Ambiente: %COMPUTERNAME%
echo Data: %DATE% - %TIME%
echo.
echo ==================================================
echo ESCOLHA UMA OPCAO:
echo ==================================================
echo.
echo 1. Executar TODOS os testes (corrigido)
echo 2. Executar apenas testes unitarios
echo 3. Executar apenas testes de integracao (corrigido)
echo 4. Executar testes com relatorio de cobertura
echo 5. Executar teste especifico
echo 6. Verificar estrutura de importacoes
echo 7. Verificar dependencias
echo 8. Limpar arquivos de cache
echo 9. SAIR
echo.
set /p opcao="Digite o numero da opcao desejada: "

if "%opcao%"=="1" goto TODOS
if "%opcao%"=="2" goto UNITARIOS
if "%opcao%"=="3" goto INTEGRACAO
if "%opcao%"=="4" goto COBERTURA
if "%opcao%"=="5" goto ESPECIFICO
if "%opcao%"=="6" goto VERIFICAR_IMPORTS
if "%opcao%"=="7" goto DEPENDENCIAS
if "%opcao%"=="8" goto LIMPAR
if "%opcao%"=="9" goto SAIR

echo Opcao invalida!
timeout /t 2 >nul
goto MENU

:TODOS
cls
echo ==================================================
echo        EXECUTANDO TODOS OS TESTES
echo ==================================================
echo.
echo Data/Hora: %DATE% - %TIME%
echo.
echo Ignorando warnings de importacao...
echo Pressione Ctrl+C para cancelar
timeout /t 2 >nul
echo.

python -m pytest tests/ -v --tb=short --maxfail=5 -p no:warnings

if %errorlevel% equ 0 (
    echo.
    echo ==================================================
    echo        ✅ TODOS OS TESTES PASSARAM!
    echo ==================================================
) else (
    echo.
    echo ==================================================
    echo        ❌ ALGUNS TESTES FALHARAM
    echo ==================================================
)

echo.
pause
goto MENU

:UNITARIOS
cls
echo ==================================================
echo        EXECUTANDO TESTES UNITARIOS
echo ==================================================
echo.
echo Data/Hora: %DATE% - %TIME%
echo.

python -m pytest tests/test_security.py tests/test_database.py tests/test_services.py -v --tb=short

if %errorlevel% equ 0 (
    echo.
    echo ==================================================
    echo        ✅ TESTES UNITARIOS PASSARAM!
    echo ==================================================
) else (
    echo.
    echo ==================================================
    echo        ❌ ALGUNS TESTES UNITARIOS FALHARAM
    echo ==================================================
)

echo.
pause
goto MENU

:INTEGRACAO
cls
echo ==================================================
echo        EXECUTANDO TESTES DE INTEGRACAO
echo ==================================================
echo.
echo Data/Hora: %DATE% - %TIME%
echo.
echo ATENCAO: Testes de integracao podem ser lentos!
echo.

python -m pytest tests/test_integration.py -v --tb=short

if %errorlevel% equ 0 (
    echo.
    echo ==================================================
    echo        ✅ TESTES DE INTEGRACAO PASSARAM!
    echo ==================================================
) else (
    echo.
    echo ==================================================
    echo        ❌ ALGUNS TESTES DE INTEGRACAO FALHARAM
    echo ==================================================
)

echo.
pause
goto MENU

:COBERTURA
cls
echo ==================================================
echo        GERANDO RELATORIO DE COBERTURA
echo ==================================================
echo.
echo Data/Hora: %DATE% - %TIME%
echo.
echo Isso pode levar alguns minutos...
echo.

python -m pytest tests/ --cov=core --cov=ui --cov=pages --cov-report=term --cov-report=html

if %errorlevel% equ 0 (
    echo.
    echo ==================================================
    echo        ✅ RELATORIO DE COBERTURA GERADO
    echo ==================================================
    echo.
    echo Relatorios disponiveis:
    echo - Terminal: (acima)
    echo - HTML: htmlcov/index.html
    echo.
    if exist htmlcov\index.html (
        start htmlcov\index.html
    )
) else (
    echo.
    echo ==================================================
    echo        ❌ ERRO AO GERAR COBERTURA
    echo ==================================================
)

echo.
pause
goto MENU

:VERIFICAR_IMPORTS
cls
echo ==================================================
echo        VERIFICANDO ESTRUTURA DE IMPORTS
echo ==================================================
echo.

echo Verificando arquivos de teste...
echo.

if exist tests\test_integration.py (
    echo ✅ test_integration.py encontrado
    echo.
    echo Verificando imports em test_integration.py:
    findstr /n "from core" tests\test_integration.py
) else (
    echo ❌ test_integration.py nao encontrado
)

echo.
echo ==================================================
echo        CORRECAO MANUAL NECESSARIA?
echo ==================================================
echo.
echo Se o erro persistir, edite manualmente o arquivo:
echo tests\test_integration.py
echo.
echo Substitua: from core.services import ...
echo Por: from core.servidor_service import ServidoresService
echo      from core.vacinacao_service import VacinacaoService
echo      etc...
echo.

pause
goto MENU

:ESPECIFICO
cls
echo ==================================================
echo        EXECUTAR TESTE ESPECIFICO
echo ==================================================
echo.
echo Testes disponiveis:
echo.
echo 1. test_security.py
echo 2. test_database.py
echo 3. test_services.py
echo 4. test_integration.py
echo 5. Executar teste por nome
echo 6. Voltar ao menu
echo.
set /p opcao_teste="Digite o numero da opcao: "

if "%opcao_teste%"=="1" goto TEST_SECURITY
if "%opcao_teste%"=="2" goto TEST_DATABASE
if "%opcao_teste%"=="3" goto TEST_SERVICES
if "%opcao_teste%"=="4" goto TEST_INTEGRATION
if "%opcao_teste%"=="5" goto TEST_BY_NAME
if "%opcao_teste%"=="6" goto MENU

echo Opcao invalida!
timeout /t 2 >nul
goto ESPECIFICO

:TEST_SECURITY
python -m pytest tests/test_security.py -v -p no:warnings
pause
goto ESPECIFICO

:TEST_DATABASE
python -m pytest tests/test_database.py -v -p no:warnings
pause
goto ESPECIFICO

:TEST_SERVICES
python -m pytest tests/test_services.py -v -p no:warnings
pause
goto ESPECIFICO

:TEST_INTEGRATION
python -m pytest tests/test_integration.py -v -p no:warnings
pause
goto ESPECIFICO

:TEST_BY_NAME
cls
echo ==================================================
echo        EXECUTAR TESTE POR NOME
echo ==================================================
echo.
set /p nome_teste="Digite o nome do teste (ex: test_login_sucesso): "

python -m pytest -k %nome_teste% -v -p no:warnings

echo.
pause
goto MENU

:DEPENDENCIAS
cls
echo ==================================================
echo        VERIFICANDO DEPENDENCIAS
echo ==================================================
echo.

echo Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python nao encontrado!
    pause
    goto MENU
)
echo ✅ Python OK
echo.

echo Verificando dependencias de teste...
echo.

python -c "import pytest" 2>nul
if %errorlevel% equ 0 (
    echo ✅ pytest instalado
) else (
    echo ❌ pytest nao instalado
)

python -c "import pytest_cov" 2>nul
if %errorlevel% equ 0 (
    echo ✅ pytest-cov instalado
) else (
    echo ❌ pytest-cov nao instalado
)

python -c "import coverage" 2>nul
if %errorlevel% equ 0 (
    echo ✅ coverage instalado
) else (
    echo ❌ coverage nao instalado
)

python -c "import pandas" 2>nul
if %errorlevel% equ 0 (
    echo ✅ pandas instalado
) else (
    echo ❌ pandas nao instalado
)

python -c "import plotly" 2>nul
if %errorlevel% equ 0 (
    echo ✅ plotly instalado
) else (
    echo ❌ plotly nao instalado
)

echo.
echo ==================================================
echo        INSTALAR DEPENDENCIAS?
echo ==================================================
echo.
echo Para instalar todas as dependencias:
echo pip install -r requirements.txt
echo.
echo Para instalar apenas dependencias de teste:
echo pip install pytest pytest-cov coverage pandas plotly
echo.
pause
goto MENU

:LIMPAR
cls
echo ==================================================
echo        LIMPANDO CACHE DO PYTEST
echo ==================================================
echo.

if exist .pytest_cache (
    echo Removendo .pytest_cache...
    rmdir /s /q .pytest_cache
    echo ✅ Cache removido
)

if exist htmlcov (
    echo Removendo htmlcov...
    rmdir /s /q htmlcov
    echo ✅ Pasta de relatorio removida
)

if exist .coverage (
    echo Removendo .coverage...
    del .coverage
    echo ✅ Dados de cobertura removidos
)

echo.
echo ✅ Limpeza concluida!
echo.
pause
goto MENU

:SAIR
cls
echo ==================================================
echo        ENCERRANDO SISTEMA DE TESTES
echo ==================================================
echo.
echo Obrigado por usar o NASST Digital!
echo.
timeout /t 2 >nul
exit