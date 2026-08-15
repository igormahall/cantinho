# Windows e Linux — o que é específico de cada um

Este arquivo é a parte de sistema operacional: assinatura de binário, antivírus,
bibliotecas que faltam, atalhos e as diferenças de comportamento entre os dois
ambientes. O que vale para os dois — comandos, ferramentas, a suíte — está em
[desenvolvimento.md](desenvolvimento.md).

---

# Windows

## O que roda, afinal

O atalho da Área de Trabalho aponta para isto:

```
.venv\Scripts\pythonw.exe  -m cantinho.main
```

Não para um `Cantinho.exe`. **Este projeto não constrói binário nenhum**, e essa
é uma decisão, não uma etapa que ficou faltando.

O `pythonw.exe` do venv é uma cópia do binário oficial da Python Software
Foundation e carrega a assinatura dela. Dá para conferir:

```powershell
Get-AuthenticodeSignature .venv\Scripts\pythonw.exe | Format-List Status, SignerCertificate
# Status: Valid
# Subject: CN=Python Software Foundation, ...
```

O `w` importa: `pythonw.exe` é o interpretador sem console, então o app abre sem
uma janela preta atrás dele.

## Por que não se gera executável

Um binário recém-construído nasce **sem assinatura e sem reputação**, e a causa
do bloqueio é estrutural, não azar. Duas coisas diferentes barram, e as duas
chegam ao mesmo lugar:

**Smart App Control**, no Windows 11 de casa, recusa *carregar* o arquivo. É o
pior dos dois para diagnosticar, porque o sintoma engana — o `.exe` continua em
disco, o duplo clique não diz absolutamente nada, e a conclusão natural é que o
build quebrou. Rebuildar não resolve: o binário novo nasce igualmente sem
assinatura.

**Antivírus gerenciado por política**, na máquina do trabalho, apaga o arquivo —
e ali não há administrador para criar exceção.

O agravante do caso do PyInstaller, que era o empacotador daqui: o `Cantinho.exe`
dele não é um programa comum, é um *bootloader* que carrega um interpretador
Python embutido e o executa da memória. Esse bootloader é **o mesmo binário** em
todo programa empacotado com PyInstaller no mundo, e como boa parte do malware
em Python também usa PyInstaller, os antivírus passaram a marcá-lo por
semelhança estrutural.

Para saber se foi o Smart App Control:

```powershell
# 1 = ligado
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy' |
    Select-Object VerifiedAndReputablePolicyState

# o nome do arquivo barrado aparece aqui, nos eventos 3033 e 3077
Get-WinEvent -LogName 'Microsoft-Windows-CodeIntegrity/Operational' -MaxEvents 50 |
    Where-Object { $_.Message -match 'Cantinho' } | Format-List TimeCreated, Id, Message
```

Um evento 3033 disparado pelo `explorer.exe` é literalmente o seu duplo clique
sendo recusado.

Sobre pagar pela assinatura, já que ela resolveria: um certificado de *code
signing* custa algumas centenas de dólares por ano e é emitido para empresa ou
para pessoa física verificada. Para um app pessoal, não se paga. E certificado
auto-assinado **não resolve** — ele não vem de uma autoridade em que o Windows
confie, e instalá-lo na raiz confiável exige justamente o administrador que não
se tem numa máquina restrita.

Daí a saída, que é a mesma nos dois casos: **não produzir binário desconhecido
nenhum**. Remover a causa, em vez de contornar o efeito. O `cantinho.spec` do
PyInstaller foi removido do repositório em 14/08/2026, e o `pyinstaller` saiu do
`requirements-dev.txt` junto — cinco pacotes a menos no passo de instalação que
precisa funcionar na máquina restrita.

## O pacote portátil: para uma máquina sem Python

Na máquina onde o repositório está clonado, o venv já resolve. O pacote portátil
existe para o outro caso: levar o Cantinho para uma máquina **que não tem Python
instalado** e onde não se pode instalar.

Pelo menu: opção **3** (dev) → **o pacote portátil**. Na mão:

```powershell
python tools\empacotar_portatil.py
python tools\empacotar_portatil.py --sem-zip     # só a pasta, sem o zip
```

Ele baixa o Python *embeddable* oficial do python.org, instala o PySide6 dentro
dele, poda o que o Qt traz e não se usa, e monta:

```
Cantinho/
  Cantinho.lnk      atalho para runtime\pythonw.exe -m cantinho.main
  Cantinho.cmd      o mesmo, para quando o atalho não sobrevive ao download
  LEIA-ME.txt
  runtime/          Python 3.12 oficial + PySide6
  app/              cantinho/ e assets/
```

É a mesma estratégia do atalho, com o runtime vindo de fora em vez de já estar
no venv. **Não há um único executável criado por este projeto** em nenhum dos
dois: o que roda é o `pythonw.exe` da PSF, e o resto são arquivos `.py`, `.qml`,
`.svg` e as DLLs assinadas do Qt que vêm do PySide6 oficial do PyPI.

Isso não é garantia de nada: nenhum antivírus publica suas regras, e um produto
gerenciado pode ter política de bloquear qualquer coisa fora de `Program Files`.
Mas o pacote fica auditável, que é o ponto.

### Instalar o portátil

1. Extrair em algum lugar sob o seu perfil — `%USERPROFILE%\Cantinho`, ou um
   pendrive. Não precisa ser `Program Files`, e é melhor que não seja.
2. Tirar a marca de "veio da internet" antes de abrir. É o que evita o aviso do
   SmartScreen:

   ```powershell
   cd $env:USERPROFILE\Cantinho
   Get-ChildItem -Recurse | Unblock-File
   ```

3. Abrir pelo `Cantinho.lnk`.

Se você tem administrador na máquina e é o **Defender** que reclama, dá para
excluir a pasta — só que isso vale para o Defender e mais nada:

```powershell
Add-MpPreference -ExclusionPath "$env:USERPROFILE\Cantinho"
```

### Se um antivírus gerenciado bloquear mesmo assim

Aí não é mais problema técnico, e o caminho é pedir a liberação a quem
administra — com o que a análise precisa:

```powershell
Get-FileHash runtime\pythonw.exe -Algorithm SHA256
(Get-AuthenticodeSignature runtime\pythonw.exe) | Format-List Status, SignerCertificate
```

O pedido é curto e verificável: *o executável é o interpretador Python oficial,
assinado pela Python Software Foundation, e o restante da pasta é código-fonte
legível. O repositório é público em `github.com/igormahall/cantinho`.*

Um binário assinado e auditável é muito mais fácil de aprovar do que um `.exe`
sem procedência.

## Não rode nada num terminal elevado

Com token de administrador o Windows põe `BUILTIN\Administradores` como dono de
todo diretório criado, no lugar do usuário. O pytest 9 endurece o próprio temp
com ACL sem herança, onde o acesso do usuário vem de "direitos do proprietário"
— que deixou de ser você.

O sintoma chega atrasado, e é isso que o torna caro: a execução elevada passa, e
a **seguinte**, normal, é que morre — a suíte com `PermissionError: [WinError 5]`
na limpeza do temp, depois de todos os testes terem passado, e o pacote portátil
no `shutil.rmtree` que refaz a pasta antes de montá-la.

O `cantinho.bat` avisa em toda ação. Se já aconteceu, apague a pasta envenenada
— e se ela resistir:

```powershell
icacls "<pasta>" /setowner "$env:COMPUTERNAME\$env:USERNAME" /t /c /q
icacls "<pasta>" /reset /t
```

**Não use `takeown /f <pasta> /r /d S` neste Windows.** A letra de confirmação
do `/d` é traduzida: em português ele responde `O valor 'S' não é permitido para
a opção '/d'`, e `/d N` significa "não". O `icacls /setowner` faz a mesma coisa
sem depender do idioma.

## O atalho da Área de Trabalho

Criado por `tools/atalho_windows.py`, no fim de `instalar` e de `atualizar`.
Diferente do `.desktop` do Linux, aqui **refazer é o certo**: quem chama é a
instalação, a pedido, e o alvo é o venv desta pasta.

- **Mudou a pasta de lugar?** Rode a opção **2** de lá. O atalho guarda caminho
  absoluto.
- **O ícone vem do asset** (`assets/icon/cantinho.ico`) e não do alvo, senão o
  atalho seria o logo do Python.
- O comando vai por `powershell -Command` e não por arquivo `.ps1`, porque
  máquina gerenciada costuma vir com a política de execução em `Restricted`, que
  bloqueia script em arquivo e deixa passar comando na linha.
- A pasta da Área de Trabalho é perguntada ao Windows, não montada como
  `%USERPROFILE%\Desktop`: em português ela tem outro nome, e com OneDrive
  corporativo está redirecionada.

---

# Linux

Três coisas só aparecem aqui: bibliotecas de sistema que o Qt carrega em
runtime, o Anaconda desligando o OpenGL, e o atalho na grade de aplicativos.
Não há Smart App Control nem executável gerado — roda-se o código direto.

## Bibliotecas de sistema

O PySide6 do PyPI traz o Qt inteiro, mas não as bibliotecas de que o Qt depende
para falar com o X11 e com o áudio. Numa Ubuntu 22.04 recém-instalada faltam
algumas, e a falha é sempre a mesma linha:

```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though
it was found.
```

O conjunto que resolve:

```bash
sudo apt install python3-venv python3-dev \
     libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
     libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 \
     libxkbcommon-x11-0 libegl1 libgl1 libdbus-1-3
```

`libxcb-cursor0` é a que mais falta: o Qt 6 passou a exigi-la e ela não vem no
desktop padrão do 22.04. Para descobrir o que ainda falta em vez de adivinhar,
`QT_DEBUG_PLUGINS=1 python -m cantinho.main`. Se o app abrir mudo, falta
`libpulse0`.

## Quando o Anaconda desliga o OpenGL

Com o ambiente `base` ativo, o `qt-main` do conda exporta
`QT_XCB_GL_INTEGRATION=none` em todo terminal — a partir de
`~/anaconda3/etc/conda/activate.d/qt-main_activate.sh`, e não do `.bashrc`.
`none` manda o Qt não carregar integração GL nenhuma, e o Qt Quick precisa de
uma.

**O app cuida disso sozinho**: remove a variável do próprio processo ao subir e
registra um aviso no log. Um valor deliberado (`xcb_glx`, `xcb_egl`) passa
intacto.

Fica documentado porque o sintoma imita o de biblioteca faltando e leva a
instalar pacote atrás de pacote sem nada mudar:

```
QXcbIntegration: Cannot create platform OpenGL context, neither GLX nor EGL
are enabled
```

O que separa os dois casos: aqui o `QT_DEBUG_PLUGINS=1` **nem chega a varrer** o
diretório `xcbglintegrations`; com `.so` ausente ele varre e falha ao carregar.

Para tirar a variável do shell de vez, `conda config --set auto_activate_base
false`. E crie o venv com o Python do sistema (`/usr/bin/python3.10 -m venv
.venv`): com o `base` ativo, o `python` do PATH é o do conda, e as bibliotecas
dele se sobrepõem às do sistema que o plugin `xcb` carrega.

## O atalho na grade de aplicativos

Na primeira abertura que não encontra um atalho, o app cria um — e depois disso
não toca mais no assunto. São dois arquivos em `~/.local/share`:
`applications/cantinho.desktop` e o ícone em `icons/hicolor/<lado>x<lado>/apps/`,
nos sete tamanhos que o `.ico` do Windows carrega.

```bash
python tools/instalar_atalho.py             # cria, se ainda não houver
python tools/instalar_atalho.py --de-novo   # reescreve o que existe
python tools/instalar_atalho.py --remover   # apaga o atalho e o ícone
```

**Mudou o repositório de pasta? Rode `--de-novo`.** O `Exec=` guarda o caminho
absoluto do Python do venv, e o app nunca sobrescreve um atalho existente — é
essa recusa que impede um clone de teste de roubar o ícone do menu apontando
para si. Execuções com `--db` não criam atalho.

**Se o ícone se comportar como antes depois de uma correção**, o problema não
está no arquivo: o GNOME Shell guarda os atalhos em memória. A instalação já
chama `update-desktop-database` e `gtk-update-icon-cache`; quando não basta,
`Alt+F2`, `r`, Enter recarrega a interface no X11 — no Wayland, sair e entrar na
sessão.

## Duas diferenças de comportamento

**O atalho global não funciona.** `Ctrl+Shift+I` é a única parte específica de
plataforma sem equivalente aqui: `create_hotkey()` devolve um no-op. A captura
de ideia continua no mural, com a janela à vista.

**A bandeja depende do desktop.** O GNOME não mostra ícone de bandeja sem a
extensão *AppIndicator and KStatusNotifierItem Support*, que vem instalada e às
vezes desligada. Isso importa porque fechar a janela **não** encerra o app. Sem
bandeja, o jeito de trazê-lo de volta é abrir de novo pelo terminal — a trava de
instância única mostra a janela que já existe. Para encerrar de verdade,
**o quarto → sair**.

O toque do quarto continua chegando nesse caso, porque ele vai por `gdbus` e não
pelo ícone da bandeja: `QSystemTrayIcon.showMessage` entrega a mensagem ao GNOME
— ela entra na lista, o ponto acende ao lado do relógio — mas não abre banner
nenhum, e um aviso que só chega na lista é o mesmo que não chegar.
