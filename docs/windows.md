# O Cantinho no Windows

Duas formas de empacotar, para dois cenários. Se a máquina é sua e você
instala o que quiser, use o PyInstaller e pare de ler na primeira seção.

A segunda existe para máquinas restritas: sem instalação, sem direito de
administrador e com antivírus gerenciado por política.

## O build normal: PyInstaller

```powershell
pip install -r requirements-dev.txt
pyinstaller cantinho.spec --noconfirm
```

- Sai `dist/Cantinho/`, uns 198 MB.
- Roda sem instalação e sem admin, inclusive de pendrive.
- É `onedir`, não `onefile`: o `onefile` descompacta em `%TEMP%` a cada
  abertura, o que é lento e costuma esbarrar em política de execução.
- O build é por plataforma — o artefato de um sistema não serve ao outro.

Pelo `cantinho.bat`, é a opção `empacotar`.

## Quando o antivírus apaga o `.exe`

Acontece, e não adianta tentar de novo. Vale entender por quê, porque a causa
é estrutural e não um azar:

- O `Cantinho.exe` do PyInstaller não é um programa comum. É um *bootloader*
  que carrega um interpretador Python inteiro embutido e o executa da memória.
- Esse bootloader é **o mesmo binário** em todo programa empacotado com
  PyInstaller no mundo. Como boa parte do malware em Python também usa
  PyInstaller, os antivírus passaram a marcá-lo por semelhança estrutural.
- Um binário assinado contestaria isso com reputação. O nosso não tem
  assinatura.

Sobre a assinatura, já que ela resolveria: um certificado de *code signing*
custa algumas centenas de dólares por ano e é emitido para empresa ou para
pessoa física verificada. Para um app pessoal, não se paga. E certificado
auto-assinado **não resolve** — ele não vem de uma autoridade em que o Windows
confie, e instalá-lo na raiz confiável exige justamente o administrador que
não se tem numa máquina restrita.

## O build portátil: sobre o Python oficial

A saída não é escapar da checagem do antivírus. É **não produzir binário
desconhecido nenhum** — remover a causa do falso positivo em vez de contornar
o efeito.

O Cantinho é código Python. O que precisa existir na máquina é um
interpretador, e há um que não dá motivo de suspeita: o `python.exe` da Python
Software Foundation, assinado por ela e com reputação acumulada em milhões de
máquinas.

```powershell
python tools\empacotar_portatil.py
python tools\empacotar_portatil.py --sem-zip     # só a pasta, sem o zip
```

Pelo `cantinho.bat`, é a opção `portatil`. Sai um
`Cantinho-portatil-windows.zip` com:

```
Cantinho/
  Cantinho.lnk      atalho para runtime\pythonw.exe -m cantinho.main
  Cantinho.cmd      o mesmo, para quando o atalho não sobrevive ao download
  LEIA-ME.txt
  runtime/          Python 3.12 oficial + PySide6
  app/              cantinho/ e assets/
```

**Não há um único executável criado por este projeto.** O que roda é o
`pythonw.exe` da PSF; o resto são arquivos `.py`, `.qml`, `.svg` e as DLLs
assinadas do Qt que vêm do PySide6 oficial do PyPI. Não existe bootloader, não
existe seção comprimida com um interpretador escondido — que são exatamente os
traços que disparam a heurística.

Isso não é garantia de nada: nenhum antivírus publica suas regras, e um
produto gerenciado pode ter política de bloquear qualquer coisa fora de
`Program Files`. Mas o pacote fica auditável, que é o ponto.

## Instalar o portátil

1. Baixar `Cantinho-portatil-windows.zip` da página de *Releases* do
   repositório.
2. Extrair em algum lugar sob o seu perfil — `%USERPROFILE%\Cantinho`, ou um
   pendrive. Não precisa ser `Program Files`, e é melhor que não seja.
3. Tirar a marca de "veio da internet" antes de abrir. É o que evita o aviso
   do SmartScreen, e é a única parte que pede PowerShell:

   ```powershell
   cd $env:USERPROFILE\Cantinho
   Get-ChildItem -Recurse | Unblock-File
   ```

4. Abrir pelo `Cantinho.lnk`.

Se você tem administrador do Windows na máquina e é o **Defender** que
reclama, dá para excluir a pasta:

```powershell
Add-MpPreference -ExclusionPath "$env:USERPROFILE\Cantinho"
```

Isso vale só para o Defender. Um antivírus de terceiros é outro produto, com
outra política, e não se altera daí.

## Se um antivírus gerenciado bloquear mesmo assim

Aí não é mais problema técnico, e o caminho é pedir a liberação a quem
administra — com o que a análise precisa:

```powershell
Get-FileHash runtime\pythonw.exe -Algorithm SHA256
(Get-AuthenticodeSignature runtime\pythonw.exe) | Format-List Status, SignerCertificate
```

O pedido é curto e verificável: *o executável é o interpretador Python
oficial, assinado pela Python Software Foundation, e o restante da pasta é
código-fonte legível. O repositório é público em
`github.com/igormahall/cantinho`.*

Um binário assinado e auditável é muito mais fácil de aprovar do que um `.exe`
sem procedência.

## Sem pacote nenhum

Se houver Python instalado e acesso ao PyPI, dá para rodar direto do código —
nada baixado pronto, nada empacotado:

```powershell
git clone https://github.com/igormahall/cantinho.git
cd cantinho
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m cantinho.main
```

É a forma com menos superfície para qualquer antivírus, e a que mais depende
de a rede deixar o `pip` sair. Se o `pip` falhar numa rede restrita, costuma
ser proxy ou certificado interno.

## Qual dos dois usar

| | `pyinstaller` | `empacotar_portatil.py` |
|---|---|---|
| o que executa | bootloader próprio, sem assinatura | `python.exe` assinado pela PSF |
| tamanho | ~198 MB | ~240 MB |
| abertura | mais rápida | um pouco mais lenta |
| usar quando | a máquina é sua | a máquina é restrita |

## Não rode nada disto num terminal elevado

Com token de administrador o Windows põe `BUILTIN\Administradores` como dono
de todo diretório criado, no lugar do usuário. O pytest 9 endurece o próprio
temp com ACL sem herança, onde o acesso do usuário vem de "direitos do
proprietário" — que deixou de ser você.

O sintoma chega atrasado, e é isso que o torna caro: a execução elevada passa,
e a **seguinte**, normal, é que morre.

- A suíte com `PermissionError: [WinError 5]` na limpeza do temp, depois de
  todos os testes terem passado.
- O `portatil` no `shutil.rmtree` que refaz a pasta antes de montar o pacote.

O `cantinho.bat` avisa em toda ação. Se já aconteceu, apague a pasta
envenenada — e se ela resistir:

```powershell
takeown /f <pasta> /r /d S
icacls <pasta> /reset /t
```

## A suíte no Windows

São **330 passados e 3 pulados**, e esse é o resultado certo, não uma suíte
incompleta. Os três são de `test_desktop_entry.py` e dependem de semântica
POSIX: barra `/` no `Exec=` e bit de execução no `.desktop`. A fixture finge o
`sys.platform`, mas o `pathlib` já escolheu `WindowsPath` na importação e o
`chmod` do Windows não tem bit para ligar — eles falhariam com o código certo,
que é o pior tipo de teste vermelho. No Linux os 333 rodam.
