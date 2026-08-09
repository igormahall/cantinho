# Levar o Cantinho para a fábrica

A máquina do trabalho tem duas restrições que definem tudo o que está aqui:
não se instala nada e não se tem administrador **do antivírus** — o V3 é
gerenciado por política, então criar exceção não é uma opção disponível.

E o V3 apaga o executável do PyInstaller.

## Por que o `.exe` some

Não é falso positivo por acaso, e não adianta tentar de novo.

O `Cantinho.exe` que sai do `pyinstaller` não é um programa comum: é um
*bootloader* que carrega um interpretador Python inteiro embutido e o executa
da memória. Esse bootloader é **o mesmo binário** em todo programa empacotado
com PyInstaller no mundo, e como boa parte do malware em Python também usa
PyInstaller, os antivírus passaram a marcá-lo por semelhança estrutural.

Um binário assinado por um editor conhecido contestaria isso com reputação. O
nosso não tem assinatura: um certificado de code signing custa algumas centenas
de dólares por ano e é emitido para empresa ou para pessoa física verificada.
Para um app pessoal, não se paga.

Certificado auto-assinado **não resolve**: ele não vem de uma autoridade em que
o Windows confie, e instalá-lo na raiz confiável exige justamente o
administrador que não temos.

Então a saída não é convencer o antivírus a aceitar um binário desconhecido. É
não produzir binário desconhecido nenhum.

## A saída: rodar sobre o Python oficial

O Cantinho é código Python. O que precisa existir na máquina é um
interpretador — e existe um interpretador que o V3 não tem motivo para tocar:
o `python.exe` distribuído pela Python Software Foundation, assinado por ela,
com reputação acumulada em milhões de máquinas.

`tools/empacotar_portatil.py` monta uma pasta com esse interpretador dentro:

```powershell
python tools/empacotar_portatil.py
```

Sai um `Cantinho-portatil-windows.zip`. Dentro dele:

```
Cantinho/
  Cantinho.lnk      atalho para runtime\pythonw.exe -m cantinho.main
  Cantinho.cmd      o mesmo, para quando o atalho não sobrevive ao download
  LEIA-ME.txt
  runtime/          Python 3.12 oficial + PySide6
  app/              cantinho/ e assets/
```

**Não há um único executável criado por este projeto.** O que roda é o
`pythonw.exe` da PSF; o resto são arquivos `.py`, `.qml`, `.svg` e as DLLs do
Qt que vêm do PySide6 oficial do PyPI. Não existe bootloader, não existe
empacotador, não existe seção comprimida com um interpretador escondido — que
são exatamente os traços que disparam a heurística.

Isso não é uma garantia: nenhum antivírus publica suas regras, e um produto
gerenciado pode ter política de bloquear qualquer coisa fora de `Program
Files`. Mas remove a causa conhecida, em vez de tentar contornar o efeito.

## Instalar na máquina da fábrica

O github.com é alcançável de lá, então o caminho é direto.

1. Baixar `Cantinho-portatil-windows.zip` da página de *Releases* do
   repositório.
2. Extrair em algum lugar sob o seu perfil — `%USERPROFILE%\Cantinho`, ou o
   pendrive. Não precisa ser `Program Files`, e é melhor que não seja.
3. Tirar a marca de "arquivo veio da internet" antes de abrir. É isto que
   evita o aviso do SmartScreen, e é a única parte que pede PowerShell:

   ```powershell
   cd $env:USERPROFILE\Cantinho
   Get-ChildItem -Recurse | Unblock-File
   ```

4. Abrir pelo `Cantinho.lnk`.

Você tem administrador do Windows na máquina, então se o **Defender** (e não o
V3) reclamar, dá para excluir a pasta:

```powershell
Add-MpPreference -ExclusionPath "$env:USERPROFILE\Cantinho"
```

Isso não afeta o V3 — são produtos diferentes, e o V3 é o que não aceita
exceção sua.

## Se mesmo assim o V3 apagar

Aí não é mais problema técnico, é de processo. Peça o allowlist ao TI com o
que eles precisam para avaliar:

```powershell
# Hash do que está sendo executado, para o chamado
Get-FileHash runtime\pythonw.exe -Algorithm SHA256
(Get-AuthenticodeSignature runtime\pythonw.exe) | Format-List Status, SignerCertificate
```

O argumento do chamado é curto e verificável: *o executável é o interpretador
Python oficial, assinado pela Python Software Foundation, e o restante da pasta
é código-fonte legível. O repositório é público em `github.com/<usuário>/cantinho`.*

Um binário assinado e auditável é um pedido muito mais fácil de aprovar do que
um `.exe` sem procedência.

## Plano C: sem pacote nenhum

Se a política bloquear a pasta inteira mas houver Python instalado na máquina e
acesso ao PyPI:

```powershell
git clone https://github.com/<usuário>/cantinho.git
cd cantinho
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m cantinho.main
```

Nenhum arquivo baixado pronto, nada empacotado. É a forma com menos superfície
para qualquer antivírus, e a que mais depende de a rede deixar o `pip` sair.

## E o `dist/Cantinho/` do PyInstaller?

Continua existindo e continua sendo o build bom para **casa**, onde o Defender
não implica com ele: é menor, abre mais rápido e é uma pasta só.

Para a fábrica, use o portátil.

| | `pyinstaller` | `empacotar_portatil.py` |
|---|---|---|
| o que executa | bootloader próprio, sem assinatura | `python.exe` assinado pela PSF |
| V3 | apaga | sem o motivo conhecido para apagar |
| tamanho | ~198 MB | ~240 MB |
| usar em | casa | fábrica |
