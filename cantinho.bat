@echo off
rem ===========================================================================
rem  Cantinho - instalacao, atualizacao e build no Windows
rem
rem  Vale para os dois casos: a primeira vez numa maquina, e a atualizacao
rem  depois de baixar o repositorio de novo e sobrescrever os arquivos. Os dois
rem  passam pelos mesmos comandos; o que muda e o que ja existe em disco.
rem
rem      cantinho.bat                 abre o menu (e o que acontece no duplo clique)
rem      cantinho.bat instalar        cria o venv e instala as dependencias
rem      cantinho.bat rodar           abre o app a partir do codigo
rem      cantinho.bat empacotar       gera dist\Cantinho\
rem      cantinho.bat atualizar       dependencias + build limpo, tudo de uma vez
rem      cantinho.bat portatil        gera o zip que passa pelo antivirus
rem      cantinho.bat testar          roda a suite
rem      cantinho.bat refazer         apaga o venv e comeca de novo
rem
rem  Os comentarios deste arquivo sao sem acento de proposito: o cmd.exe le o
rem  .bat byte a byte e o codigo de pagina do console nao e garantido antes da
rem  linha do chcp.
rem ===========================================================================

setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1

rem A pasta do proprio script, e nao o diretorio atual. E o que faz funcionar
rem tanto no duplo clique quanto chamado de outro lugar, e sobrevive a nomes de
rem pasta com espaco e ponto ("5. Projetos").
cd /d "%~dp0"

set "VENV=.venv"
set "PY=%VENV%\Scripts\python.exe"
set "TITULO=Cantinho"
title %TITULO%

if not exist "requirements-dev.txt" (
    echo.
    echo  Este script precisa rodar de dentro da pasta do Cantinho.
    echo  Nao encontrei requirements-dev.txt em: %CD%
    echo.
    echo  Se voce extraiu o zip do GitHub, confira se os arquivos ficaram na
    echo  raiz e nao dentro de uma subpasta "cantinho-main".
    goto :fim_erro
)

if "%~1"=="" goto :menu
set "ACAO=%~1"
goto :despachar

rem ---------------------------------------------------------------- o menu

:menu
echo.
echo   Cantinho
echo   %CD%
echo.
echo    1  instalar ou atualizar o ambiente ^(venv + dependencias^)
echo    2  rodar o Cantinho a partir do codigo
echo    3  gerar o executavel em dist\Cantinho\
echo    4  atualizar tudo depois de sobrescrever os arquivos
echo    5  gerar o pacote portatil ^(o que passa pelo antivirus da fabrica^)
echo    6  rodar os testes
echo    7  refazer o ambiente do zero
echo    0  sair
echo.
set "ESCOLHA="
set /p "ESCOLHA=  o que voce quer fazer? "

if "%ESCOLHA%"=="1" set "ACAO=instalar"
if "%ESCOLHA%"=="2" set "ACAO=rodar"
if "%ESCOLHA%"=="3" set "ACAO=empacotar"
if "%ESCOLHA%"=="4" set "ACAO=atualizar"
if "%ESCOLHA%"=="5" set "ACAO=portatil"
if "%ESCOLHA%"=="6" set "ACAO=testar"
if "%ESCOLHA%"=="7" set "ACAO=refazer"
if "%ESCOLHA%"=="0" goto :fim_ok

if not defined ACAO (
    echo.
    echo  Nao entendi. Escolha um numero da lista.
    goto :menu
)
set "PAUSAR=1"

rem ------------------------------------------------------------- despacho

:despachar
if /i "%ACAO%"=="instalar"   goto :instalar
if /i "%ACAO%"=="rodar"      goto :rodar
if /i "%ACAO%"=="empacotar"  goto :empacotar
if /i "%ACAO%"=="atualizar"  goto :atualizar
if /i "%ACAO%"=="portatil"   goto :portatil
if /i "%ACAO%"=="testar"     goto :testar
if /i "%ACAO%"=="refazer"    goto :refazer

echo.
echo  Comando desconhecido: %ACAO%
echo  Use: instalar ^| rodar ^| empacotar ^| atualizar ^| portatil ^| testar ^| refazer
goto :fim_erro

rem ------------------------------------------------------------- o ambiente

:instalar
call :garantir_ambiente || goto :fim_erro
echo.
echo  Ambiente pronto.
echo  Para abrir o app:  cantinho.bat rodar
goto :fim_ok

:refazer
echo.
echo  Isto apaga %VENV% e reinstala tudo. O seu banco de eventos nao esta ai
echo  dentro e nao e tocado.
set "CONFIRMA="
set /p "CONFIRMA=  apagar o ambiente? (s/N) "
if /i not "%CONFIRMA%"=="s" goto :fim_ok
if exist "%VENV%" (
    echo  apagando %VENV% ...
    rmdir /s /q "%VENV%"
)
if exist "build\cantinho" rmdir /s /q "build\cantinho"
call :garantir_ambiente || goto :fim_erro
echo.
echo  Ambiente refeito.
goto :fim_ok

rem --------------------------------------------------------------- o app

:rodar
call :garantir_ambiente || goto :fim_erro
echo.
echo  Abrindo o Cantinho. Feche esta janela so depois de fechar o app.
"%PY%" -m cantinho.main
goto :fim_ok

:testar
call :garantir_ambiente || goto :fim_erro
echo.
"%PY%" -m pytest
if errorlevel 1 goto :fim_erro
goto :fim_ok

rem ------------------------------------------------------------- os builds

:atualizar
rem O caminho da atualizacao manual: voce baixou o repositorio de novo, jogou
rem os arquivos por cima, e quer o executavel refeito com o que chegou.
rem
rem A diferenca para "empacotar" e uma so: o cache de analise do PyInstaller em
rem build\cantinho vai embora antes. Ele e valido quase sempre, e "quase" e
rem pouco quando os arquivos foram trocados por baixo dele - um build que
rem embute a versao velha de um .qml e o tipo de erro que so aparece na tela,
rem depois, sem mensagem nenhuma.
call :garantir_ambiente || goto :fim_erro
if exist "build\cantinho" (
    echo.
    echo  limpando o cache de build ...
    rmdir /s /q "build\cantinho"
)
call :construir || goto :fim_erro
goto :fim_ok

:empacotar
call :garantir_ambiente || goto :fim_erro
call :construir || goto :fim_erro
goto :fim_ok

:portatil
rem O empacotador que nao gera binario nenhum: monta o app sobre o python.exe
rem oficial da PSF, que ja vem assinado. Existe porque o antivirus corporativo
rem apaga o executavel do PyInstaller - o bootloader dele e o mesmo binario em
rem todo programa empacotado com ele, inclusive nos maliciosos.
call :garantir_ambiente || goto :fim_erro
echo.
"%PY%" tools\empacotar_portatil.py
if errorlevel 1 goto :fim_erro
goto :fim_ok

rem =========================================================== sub-rotinas

:garantir_ambiente
rem Idempotente: na primeira vez cria o venv, nas seguintes so confere e
rem atualiza as dependencias. E o mesmo comando para instalar e para atualizar.
call :avisar_admin

if exist "%PY%" (
    "%PY%" --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  O ambiente em %VENV% nao responde ^(o Python dele pode ter sido
        echo  desinstalado ou movido^). Refazendo do zero.
        rmdir /s /q "%VENV%"
    )
)

if not exist "%PY%" (
    call :achar_python || exit /b 1
    echo.
    echo  criando o ambiente em %VENV% ...
    !BOOT! -m venv "%VENV%"
    if errorlevel 1 (
        echo.
        echo  Nao consegui criar o ambiente virtual.
        exit /b 1
    )
)

echo.
echo  conferindo as dependencias ...
"%PY%" -m pip install --disable-pip-version-check --quiet --upgrade pip
"%PY%" -m pip install --disable-pip-version-check -r requirements-dev.txt
if errorlevel 1 (
    echo.
    echo  Falhou instalar as dependencias.
    echo  Numa rede corporativa isso costuma ser proxy ou certificado; o
    echo  arquivo docs\fabrica.md tem o que fazer nesse caso.
    exit /b 1
)
exit /b 0


:achar_python
rem O lancador "py" primeiro: ele acha a instalacao mesmo sem PATH, que e como
rem o instalador oficial deixa a maquina quando ninguem marca a caixinha.
set "BOOT="
py -3 --version >nul 2>&1
if not errorlevel 1 set "BOOT=py -3"
if not defined BOOT (
    python --version >nul 2>&1
    if not errorlevel 1 set "BOOT=python"
)
if not defined BOOT (
    echo.
    echo  Nao encontrei o Python. Instale a versao 3.10 ou mais nova de
    echo  python.org e marque "Add python.exe to PATH".
    exit /b 1
)
exit /b 0


:construir
rem O executavel nao pode ser reescrito enquanto esta aberto, e o erro do
rem PyInstaller nesse caso fala de permissao, o que manda procurar o defeito no
rem antivirus em vez de na janela que ficou aberta atras.
tasklist /fi "imagename eq Cantinho.exe" 2>nul | find /i "Cantinho.exe" >nul
if not errorlevel 1 (
    echo.
    echo  O Cantinho esta aberto. Feche o app ^(e o icone da bandeja^) antes de
    echo  gerar o executavel de novo.
    exit /b 1
)

echo.
echo  gerando o executavel. Leva um ou dois minutos.
"%PY%" -m PyInstaller cantinho.spec --noconfirm
if errorlevel 1 (
    echo.
    echo  O build falhou.
    exit /b 1
)
echo.
echo  Pronto: "%CD%\dist\Cantinho\Cantinho.exe"
exit /b 0


:avisar_admin
rem O PyInstaller 7 vai bloquear build como administrador, e o 6 ja reclama.
net session >nul 2>&1
if not errorlevel 1 (
    echo.
    echo  Aviso: este terminal esta como administrador. Nada aqui precisa
    echo  disso, e o PyInstaller reclama. Prefira um terminal comum.
)
exit /b 0

rem ================================================================== saida

:fim_ok
if defined PAUSAR pause
endlocal
exit /b 0

:fim_erro
echo.
if defined PAUSAR pause
endlocal
exit /b 1
