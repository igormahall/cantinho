@echo off
rem ===========================================================================
rem  Cantinho - a porta de entrada no Windows
rem
rem      cantinho.bat              o menu, que e o que o duplo clique abre
rem      cantinho.bat instalar     monta o quarto do zero e deixa o atalho
rem      cantinho.bat atualizar    troca o que mudou e refaz o atalho
rem      cantinho.bat dev          a oficina: codigo, testes, ferramentas
rem      cantinho.bat remover      desmonta, e pergunta o que fica
rem
rem  Sao quatro verbos e mais nenhum. Este arquivo e so do Windows - o roteiro
rem  do Ubuntu vive no README.md, que e onde alguem de la vai procurar.
rem
rem  POR QUE NAO SE GERA EXECUTAVEL AQUI
rem
rem  Um binario recem-construido nasce sem assinatura e sem reputacao. O Smart
rem  App Control do Windows 11 recusa carrega-lo e o antivirus gerenciado da
rem  maquina restrita o apaga - e nos dois casos nao ha administrador para
rem  criar excecao. O sintoma engana: o arquivo continua em disco, o duplo
rem  clique nao diz nada, e parece defeito do build. Quem conta a verdade e o
rem  log Microsoft-Windows-CodeIntegrity/Operational, eventos 3033 e 3077.
rem
rem  O que roda e o pythonw.exe do proprio venv - copia do binario oficial da
rem  Python Software Foundation, que carrega a assinatura dela. O atalho da
rem  Area de Trabalho aponta para ele com "-m cantinho.main". Nao ha binario
rem  construido aqui, entao nao ha o que ser bloqueado. Ver docs/plataformas.md.
rem
rem  Os comentarios e as mensagens sao sem acento de proposito: o cmd.exe le o
rem  .bat byte a byte e o codigo de pagina do console nao e garantido.
rem ===========================================================================

setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1

rem A pasta do proprio script, e nao o diretorio atual. E o que faz funcionar
rem tanto no duplo clique quanto chamado de outro lugar, e sobrevive a nomes de
rem pasta com espaco e com ponto no nome.
cd /d "%~dp0"

set "VENV=.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PYW=%VENV%\Scripts\pythonw.exe"
set "DIARIO=%APPDATA%\Cantinho"
title Cantinho

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
echo    1  instalar    montar o quarto do zero, atalho incluido
echo    2  atualizar   trocar o que mudou; o que voce anotou fica
echo    3  dev         a oficina: codigo, testes, ferramentas
echo    4  remover     desmontar, e escolher o que fica
echo    0  sair
echo.
set "ESCOLHA="
set /p "ESCOLHA=  o que vai ser? "

rem Enter sozinho sai, como o 0. Alem de ser o que a pessoa espera, e o que
rem impede o menu de girar para sempre quando nao ha ninguem digitando: sem
rem console, o "set /p" devolve na hora e sem alterar a variavel.
if not defined ESCOLHA goto :fim_ok

set "ACAO="
if "%ESCOLHA%"=="1" set "ACAO=instalar"
if "%ESCOLHA%"=="2" set "ACAO=atualizar"
if "%ESCOLHA%"=="3" set "ACAO=dev"
if "%ESCOLHA%"=="4" set "ACAO=remover"
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
if /i "%ACAO%"=="atualizar"  goto :atualizar
if /i "%ACAO%"=="dev"        goto :dev
if /i "%ACAO%"=="remover"    goto :remover

echo.
echo  Comando desconhecido: %ACAO%
echo  Use: instalar ^| atualizar ^| dev ^| remover
goto :fim_erro

rem =========================================================== 1  instalar

:instalar
rem Do zero, como o nome diz: o ambiente antigo sai inteiro. E o caminho de
rem quem esta comecando nesta maquina, e tambem o de quem tem um venv em
rem estado duvidoso e quer parar de adivinhar.
call :avisar_admin
echo.
echo  Montando o quarto do zero.
echo  Uns cinco a dez minutos, quase tudo esperando o pip baixar o PySide6.
echo  O seu diario fica em %DIARIO%, e nada disto encosta nele.

if exist "%VENV%" (
    echo.
    echo  Ja existe um ambiente em %VENV%, e ele sai inteiro para o novo entrar.
    echo  Se voce so quer o que mudou, a opcao 2 faz isso sem apagar nada.
    set "CONFIRMA="
    set /p "CONFIRMA=  refazer do zero? (s/N) "
    if /i not "!CONFIRMA!"=="s" goto :fim_ok
)

call :fechar_app
call :achar_python || goto :fim_erro

if exist "%VENV%" (
    echo.
    echo  tirando o ambiente antigo ...
    rmdir /s /q "%VENV%"
)
if exist "build\cantinho" rmdir /s /q "build\cantinho"
call :limpar_exe_bloqueado

echo.
echo  levantando o ambiente em %VENV% ...
!BOOT! -m venv "%VENV%"
if errorlevel 1 (
    echo.
    echo  Nao consegui criar o ambiente virtual.
    goto :fim_erro
)

call :dependencias || goto :fim_erro
call :criar_atalho
goto :pronto

rem ========================================================== 2  atualizar

:atualizar
rem Depois de "git pull" ou de descompactar o zip novo por cima. Nada e
rem apagado: o venv que ja existe e reaproveitado e so as dependencias sao
rem conferidas. Se nao houver ambiente nenhum, isto vira uma instalacao.
call :avisar_admin
echo.
echo  Arrumando o quarto.
echo  Troca so o codigo. O seu diario fica em %DIARIO%, intocado.

call :fechar_app
call :puxar_do_git

if not exist "%PY%" (
    echo.
    echo  Ainda nao ha ambiente em %VENV%. Entao e montar, e nao arrumar.
    call :achar_python || goto :fim_erro
    !BOOT! -m venv "%VENV%"
    if errorlevel 1 (
        echo.
        echo  Nao consegui criar o ambiente virtual.
        goto :fim_erro
    )
)

rem O venv guarda o caminho absoluto do Python que o criou. Se ele parou de
rem responder, o Python de base foi desinstalado ou movido - refazer e mais
rem barato do que descobrir isso pelo erro seguinte, que fala de outra coisa.
"%PY%" --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  O ambiente em %VENV% nao responde mais. Levantando outro.
    rmdir /s /q "%VENV%"
    call :achar_python || goto :fim_erro
    !BOOT! -m venv "%VENV%"
    if errorlevel 1 goto :fim_erro
)

if exist "build\cantinho" rmdir /s /q "build\cantinho"
call :limpar_exe_bloqueado
call :dependencias || goto :fim_erro
call :criar_atalho
goto :pronto

rem ================================================================ 3  dev

:dev
call :exigir_ambiente || goto :fim_erro
echo.
echo   A oficina
echo.
echo    1  abrir o Cantinho a partir do codigo
echo    2  a suite de testes
echo    3  o estilo do codigo ^(ruff + qmllint^)
echo    4  percorrer a interface clicando, nos dois temas
echo    5  um banco de demonstracao, com duas semanas de uso
echo    6  o pacote portatil, para uma maquina sem Python
echo    0  voltar
echo.
set "TAREFA="
set /p "TAREFA=  o que vai ser? "

if not defined TAREFA goto :fim_ok
if "%TAREFA%"=="0" goto :fim_ok
if "%TAREFA%"=="1" goto :dev_rodar
if "%TAREFA%"=="2" goto :dev_testar
if "%TAREFA%"=="3" goto :dev_lint
if "%TAREFA%"=="4" goto :dev_simular
if "%TAREFA%"=="5" goto :dev_semear
if "%TAREFA%"=="6" goto :dev_portatil
echo.
echo  Nao entendi. Escolha um numero da lista.
goto :dev

:dev_rodar
echo.
echo  Abrindo o Cantinho pelo codigo. Esta janela fica presa ate ele fechar.
"%PY%" -m cantinho.main
goto :dev

:dev_testar
echo.
rem No Windows o resultado certo e 461 passados e 3 pulados: os tres sao de
rem test_desktop_entry.py e dependem de semantica POSIX que nao existe aqui.
"%PY%" -m pytest
pause
goto :dev

:dev_lint
rem O ruff nao esta em requirements-dev.txt: aquele arquivo e o que roda na
rem maquina restrita, sem internet confiavel, e uma dependencia a mais ali e
rem uma chance a mais de a instalacao falhar onde ela mais importa. Lint nao e
rem o que faz o app rodar. Por isso a falta dele aqui e um aviso, nao um erro.
rem O qmllint vem junto com o PySide6 e nao precisa de nada instalado.
echo.
"%PY%" -m ruff --version >nul 2>&1
if errorlevel 1 (
    echo  O ruff nao esta instalado, entao a parte Python fica de fora:
    echo.
    echo      %PY% -m pip install -r requirements-lint.txt
    echo.
) else (
    echo  ruff:
    "%PY%" -m ruff check cantinho tests tools
    echo.
)
echo  qmllint:
"%PY%" tools\check_qml.py
pause
goto :dev

:dev_simular
rem E o que cobre o QML - o pytest nao cobre. Os dois temas, porque sem --tema
rem ele herda o modo auto, que decide pelo relogio: como o desenvolvimento
rem acontece a noite, na pratica o tema claro nunca era exercitado.
echo.
echo  Isto clica na interface de verdade, entao DEIXE A TELA LIGADA: com o
echo  monitor apagado o Qt para de apresentar quadros, as animacoes congelam
echo  e o roteiro falha em cascata como se a interface estivesse quebrada.
echo.
pause
"%PY%" tools\simular_uso.py --tema tarde
if errorlevel 1 goto :dev_simular_fim
"%PY%" tools\simular_uso.py --tema noite
:dev_simular_fim
pause
goto :dev

:dev_semear
rem Um banco vazio nao mostra quase nada: sem isto, avaliar estante, planta,
rem mural ou bilhete exige usar o app por duas semanas.
echo.
"%PY%" tools\semear.py
pause
goto :dev

:dev_portatil
rem O pacote para uma maquina que nao tem Python. Aqui nao e preciso: o atalho
rem ja roda sobre o pythonw.exe assinado do venv. Ele monta o app sobre o
rem python.exe oficial da PSF e nao constroi binario nenhum, pela mesma razao
rem que o atalho aponta para o venv.
echo.
"%PY%" tools\empacotar_portatil.py
pause
goto :dev

rem ============================================================ 4  remover

:remover
rem Desmontar tem duas perguntas, e elas sao separadas de proposito: o
rem ambiente da para refazer com a opcao 1 a qualquer momento, e o diario nao
rem da para refazer com nada. Misturar as duas numa confirmacao so seria pedir
rem que a pressa apagasse a unica coisa insubstituivel daqui.
echo.
echo  Desmontar o Cantinho.
echo.
echo   sai:   o ambiente em %VENV%, as pastas de trabalho, o pacote portatil
echo          e o atalho da Area de Trabalho
echo   fica:  o codigo desta pasta, e o seu diario em
echo          %DIARIO%
echo.
echo  O diario e a unica coisa aqui que nao se refaz, entao ele so sai se voce
echo  pedir - e a pergunta dele vem separada, depois desta.
echo.
set "CONFIRMA="
set /p "CONFIRMA=  desmontar? (s/N) "
if /i not "!CONFIRMA!"=="s" (
    echo.
    echo  Entao fica tudo como estava.
    goto :fim_ok
)

call :fechar_app
call :remover_atalho

echo.
echo  tirando o que foi montado ...
call :apagar_se_existir "%VENV%"
call :apagar_se_existir "build"
call :apagar_se_existir "dist"
call :apagar_se_existir "portatil"
if exist "Cantinho-portatil-windows.zip" (
    echo    - Cantinho-portatil-windows.zip
    del /q "Cantinho-portatil-windows.zip"
)

echo.
echo  Feito. O que sobrou desta pasta e o codigo, e ele cabe na lixeira.
echo.
echo  Falta o diario:
echo      %DIARIO%
echo.
echo  Sao as suas tarefas, sessoes, ideias e as paginas exportadas, desde o
echo  primeiro dia. Nao existe copia em lugar nenhum e nao ha volta. Se voce
echo  quiser guardar antes, o banco inteiro e um arquivo so: cantinho.db
echo.
echo  Para apagar mesmo, escreva a palavra  apagar  e aperte Enter.
echo  Qualquer outra coisa deixa o diario onde esta.
echo.
set "SENTENCA="
set /p "SENTENCA=  o diario: "
if /i not "!SENTENCA!"=="apagar" (
    echo.
    echo  O diario fica. Ele continua ali, esperando o quarto ser montado de
    echo  novo - a opcao 1 devolve tudo como estava, com o que voce anotou.
    goto :fim_ok
)

if exist "%DIARIO%" rmdir /s /q "%DIARIO%"
echo.
echo  O diario foi apagado. O quarto ficou vazio.
goto :fim_ok

rem =========================================================== sub-rotinas

:dependencias
echo.
echo  conferindo as dependencias ...
"%PY%" -m pip install --disable-pip-version-check --quiet --upgrade pip
"%PY%" -m pip install --disable-pip-version-check -r requirements-dev.txt
if errorlevel 1 (
    echo.
    echo  Falhou instalar as dependencias.
    echo  Numa rede restrita isso costuma ser proxy ou certificado; o
    echo  arquivo docs\plataformas.md tem o que fazer nesse caso.
    exit /b 1
)
exit /b 0


:exigir_ambiente
if exist "%PY%" exit /b 0
echo.
echo  Ainda nao ha ambiente em %VENV%. A opcao 1 monta ele.
exit /b 1


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
    echo  Nao encontrei o Python nesta maquina. Instale a versao 3.10 ou mais
    echo  nova de python.org e marque "Add python.exe to PATH".
    exit /b 1
)
exit /b 0


:criar_atalho
rem O ultimo passo: sem ele a pessoa termina o roteiro inteiro e nao acha o
rem programa em lugar nenhum. Falhar aqui e aviso e nao erro, entao o codigo
rem de saida e ignorado de proposito - sem atalho o app ainda abre pela
rem oficina.
echo.
"%PY%" tools\atalho_windows.py
exit /b 0


:remover_atalho
rem O tools\atalho_windows.py nao importa PySide6, entao qualquer Python 3
rem serve. Isso importa aqui: numa pasta que ja perdeu o venv, o atalho ainda
rem precisa sair da Area de Trabalho.
if exist "%PY%" (
    "%PY%" tools\atalho_windows.py --remover
    exit /b 0
)
py -3 tools\atalho_windows.py --remover >nul 2>&1
if not errorlevel 1 exit /b 0
python tools\atalho_windows.py --remover >nul 2>&1
exit /b 0


:apagar_se_existir
if not exist "%~1" exit /b 0
echo    - %~1
rmdir /s /q "%~1"
exit /b 0


:fechar_app
rem O app tem que estar fechado para as dependencias serem trocadas: as DLLs
rem do Qt ficam em uso enquanto ele roda, e o pip falha ao substitui-las.
rem
rem A busca e pela linha de comando e nao pelo nome do processo: "pythonw.exe"
rem sozinho pegaria qualquer outro programa em Python aberto na maquina. Sao
rem dois processos por app aberto - o lancador do venv e o Python de base que
rem ele chama -, e os dois carregam "cantinho.main" na linha.
rem
rem Fechar assim e TerminateProcess, entao o aboutToQuit nao roda e uma sessao
rem em andamento fica sem fim no log. Isso ja tem rede: na abertura seguinte a
rem sessao e fechada na ultima marca de vida (services/heartbeat.py), com
rem perda de ate um tique de um minuto. E o mesmo caminho de uma queda de
rem energia, e o app avisa na tela quando acontece.
powershell -NoProfile -NonInteractive -Command "$alvo = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*.exe' -and $_.CommandLine -like '*cantinho.main*' }; if ($alvo) { $alvo | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } ; exit 10 } else { exit 0 }"
if errorlevel 10 (
    echo.
    echo  O Cantinho estava aberto, e eu fechei a porta para poder trocar as
    echo  coisas de lugar. Se havia uma sessao correndo, ela e guardada ate a
    echo  ultima marca de vida quando o app abrir de novo - e ele mesmo conta
    echo  isso na tela.
)
rem O executavel antigo, para quem vem de uma instalacao que ainda o tinha.
taskkill /f /im Cantinho.exe >nul 2>&1
exit /b 0


:limpar_exe_bloqueado
rem O dist\Cantinho\Cantinho.exe de instalacoes antigas e uma armadilha: ele
rem continua em disco, o duplo clique nele nao faz nada e nao diz nada, e a
rem conclusao natural e que o app quebrou. Nada mais aponta para ele.
if not exist "dist\Cantinho" exit /b 0
echo.
echo  tirando o dist\Cantinho, que o Windows bloqueia e ninguem mais usa ...
rmdir /s /q "dist\Cantinho"
exit /b 0


:puxar_do_git
rem So quando faz sentido: pasta que veio de "git clone" e git no PATH. Numa
rem pasta vinda do zip isto nao aparece, porque la a atualizacao e descompactar
rem por cima - e "git pull" responderia "not a git repository".
if not exist ".git" exit /b 0
git --version >nul 2>&1
if errorlevel 1 exit /b 0
echo.
set "PUXAR="
set /p "PUXAR=  buscar as novidades no GitHub antes? (S/n) "
if /i "!PUXAR!"=="n" exit /b 0
git pull --rebase
if errorlevel 1 (
    echo.
    echo  O git pull nao terminou. Sigo com os arquivos que ja estao aqui -
    echo  resolva o conflito e rode a atualizacao de novo.
)
exit /b 0


:avisar_admin
rem Com o token elevado, o Windows poe BUILTIN\Administradores como dono de
rem todo diretorio criado, no lugar do usuario. Quem endurece a propria pasta
rem com ACL sem heranca - o pytest faz isso no temp desde a versao 9 - concede
rem o acesso por "direitos do proprietario", e o proprietario deixou de ser
rem voce. O sintoma chega atrasado, e e isso que o torna caro: a execucao
rem elevada passa, e a seguinte, normal, e que morre.
net session >nul 2>&1
if not errorlevel 1 (
    echo.
    echo  Aviso: este terminal esta como administrador, e nada aqui precisa
    echo  disso. Tudo o que for criado fica com o dono errado, e as pastas
    echo  passam a resistir a quem tentar apaga-las de uma sessao comum -
    echo  numa execucao seguinte, o que faz o erro parecer vir de outro lugar.
    echo  Prefira um terminal comum. O conserto, se ja aconteceu, esta em
    echo  docs\plataformas.md.
)
exit /b 0

rem ================================================================== saida

:pronto
echo.
echo  Pronto. O atalho "Cantinho" esta na Area de Trabalho, e o duplo clique
echo  nele abre a porta. Nao ha mais nada para rodar depois disto.
echo.
if defined PAUSAR (
    set "ABRIR="
    set /p "ABRIR=  abrir o Cantinho agora? (S/n) "
    if /i not "!ABRIR!"=="n" start "" "%PYW%" -m cantinho.main
)
goto :fim_ok

:fim_ok
if defined PAUSAR pause
endlocal
exit /b 0

:fim_erro
echo.
if defined PAUSAR pause
endlocal
exit /b 1
