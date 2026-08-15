"""Empacota o Cantinho sobre o Python embeddable oficial, sem construir binário.

Por que este empacotador existe
-------------------------------

Na máquina onde o repositório está clonado, o venv já resolve: o
`.venv\\Scripts\\pythonw.exe` é cópia do binário oficial da Python Software
Foundation e carrega a assinatura dela, e é para ele que o atalho da Área de
Trabalho aponta.

Este pacote é para o outro caso — levar o Cantinho a uma máquina **que não tem
Python** e onde não se pode instalar nada. Mesma estratégia, com o runtime
vindo de fora: ele baixa o Python *embeddable* do python.org e monta o app em
cima dele.

O que ela **não** faz é gerar um executável próprio, e isso é o ponto. Um
binário recém-construído nasce sem assinatura e sem reputação; o antivírus
gerenciado da máquina restrita apaga, o Smart App Control do Windows 11 recusa
carregar, e não há administrador para criar exceção em nenhum dos dois casos.
A saída não é contornar a checagem: é não dar o que checar.

Não existe nenhum binário construído aqui. Só arquivos `.py`, os `.qml`, os
`.svg`, e DLLs assinadas do Qt vindas do PySide6 oficial.

O que sai
---------

    portatil/Cantinho/
      Cantinho.lnk        atalho: pythonw.exe -m cantinho.main, sem console
      Cantinho.cmd        o mesmo, para quando atalho não sobrevive ao download
      LEIA-ME.txt         instruções de quem só recebeu a pasta
      runtime/            Python 3.12 embeddable + PySide6
      app/                cantinho/ e assets/

    Cantinho-portatil-windows.zip

Uso
---

    python tools/empacotar_portatil.py
    python tools/empacotar_portatil.py --sem-zip     # só a pasta
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

# Como o Python põe no sys.path o diretório do script e não o diretório atual,
# a raiz do repositório entra aqui na mão. Sem isto, `import cantinho` falha
# mesmo rodando da raiz.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Fixo, e não `sys.version_info`: o pacote embeddable precisa ser exatamente a
# mesma minor version do PySide6 que vamos instalar dentro dele, e queremos que
# o pacote gerado na máquina de casa seja idêntico ao gerado em qualquer outra.
PYTHON_VERSAO = "3.12.10"
PYTHON_ZIP = f"python-{PYTHON_VERSAO}-embed-amd64.zip"
PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSAO}/{PYTHON_ZIP}"

DESTINO = RAIZ / "portatil"
CACHE = RAIZ / "build" / "cache-portatil"
ZIP_FINAL = RAIZ / "Cantinho-portatil-windows.zip"

# O PySide6 do PyPI traz
# o Qt inteiro, e o WebEngine sozinho passa de 150 MB numa pasta que precisa
# caber em pendrive. Nada aqui é importado pelo app.
FORA = (
    "WebEngine",
    "Qt6Pdf",
    "Quick3D",
    "Qt63D",
    "Charts",
    "DataVisualization",
    "Designer",
    "Bluetooth",
    "Nfc",
    "SerialPort",
    "Sensors",
    "Qt6Sql",
    "Qt6Test",
    "Qt6Help",
    "QtWebEngine",
    "Qt3D",
    "examples",
    "glue",
    "typesystems",
    "include",
)

# Pastas inteiras do PySide6 que não servem a este app.
#
# `resources/` são os .pak e o icudtl.dat do WebEngine — 100 MB de um módulo
# que já sai pelos excludes. `translations/` são as traduções do próprio Qt,
# que só valem para quem chama QTranslator; a interface daqui é texto em QML.
# `metatypes/` e `typesystems/` servem à geração de binding, não à execução.
PASTAS_FORA = (
    "resources",
    "translations",
    "metatypes",
    "typesystems",
    "include",
    "glue",
    "examples",
    "scripts",
    "support",
    "qml/QtQuick3D",
    "qml/QtWebEngine",
    "qml/QtCharts",
    "qml/QtDataVisualization",
)

LEIA_ME = """Cantinho — versão portátil para Windows
========================================

Não precisa instalar nada e não precisa de administrador.

COMO ABRIR

    Clique duas vezes em  Cantinho.lnk

    Se o atalho não funcionar (alguns downloads perdem o atalho),
    use  Cantinho.cmd  — faz exatamente a mesma coisa.

SE O WINDOWS AVISAR "Windows protegeu o seu computador"

    Clique em "Mais informações" e depois em "Executar assim mesmo".
    Isso acontece porque o arquivo veio da internet, e some depois da
    primeira vez.

    Para evitar o aviso, antes de abrir rode no PowerShell, dentro
    desta pasta:

        Get-ChildItem -Recurse | Unblock-File

ONDE FICAM OS SEUS DADOS

    %APPDATA%\\Cantinho\\cantinho.db

    Nada sai da máquina. Não há conta, nuvem nem sincronização.
    Para levar seus dados junto, copie esse arquivo.

    Para testar sem mexer nos seus dados de verdade:

        Cantinho.cmd --db teste.db

O QUE TEM AQUI DENTRO

    runtime/   Python 3.12 oficial (python.org) + PySide6
    app/       o código do Cantinho e os desenhos

    Não há nenhum executável criado por este projeto: o que roda é o
    python.exe da Python Software Foundation, assinado por ela.
"""


def log(mensagem: str) -> None:
    print(mensagem, flush=True)


def baixar_python() -> Path:
    """Baixa o pacote embeddable, com cache em build/."""
    CACHE.mkdir(parents=True, exist_ok=True)
    alvo = CACHE / PYTHON_ZIP
    if alvo.is_file():
        log(f"  cache: {alvo.relative_to(RAIZ)}")
        return alvo

    log(f"  baixando {PYTHON_URL}")
    with urllib.request.urlopen(PYTHON_URL, timeout=120) as resposta:
        dados = resposta.read()
    alvo.write_bytes(dados)
    digest = hashlib.sha256(dados).hexdigest()
    log(f"  {len(dados) / 1024 / 1024:.1f} MB, sha256 {digest[:16]}…")
    return alvo


def montar_runtime(runtime: Path) -> None:
    """Extrai o embeddable e abre o sys.path dele para o resto do pacote."""
    zip_python = baixar_python()
    runtime.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_python) as z:
        z.extractall(runtime)

    # O embeddable vem com o sys.path trancado num `._pth` e com o `site`
    # desligado — é assim que ele fica isolado do Python instalado na máquina.
    # Precisamos de três coisas nele: as bibliotecas que vamos instalar, o
    # diretório do app, e o `site` ligado (o PySide6 registra o diretório das
    # DLLs do Qt na importação, e isso depende do site).
    pth = runtime / f"python{PYTHON_VERSAO.split('.')[0]}{PYTHON_VERSAO.split('.')[1]}._pth"
    pth.write_text(
        "\n".join(
            [
                f"python{PYTHON_VERSAO.split('.')[0]}{PYTHON_VERSAO.split('.')[1]}.zip",
                ".",
                "Lib\\site-packages",
                "..\\app",
                "",
                "import site",
                "",
            ]
        ),
        encoding="utf-8",
    )


def instalar_pyside(runtime: Path) -> None:
    """Instala o PySide6 dentro do runtime, com o pip do venv atual."""
    destino = runtime / "Lib" / "site-packages"
    destino.mkdir(parents=True, exist_ok=True)
    requisitos = (RAIZ / "requirements.txt").read_text(encoding="utf-8").strip()
    log(f"  pip install {requisitos} --target {destino.relative_to(RAIZ)}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-compile",
            "--target",
            str(destino),
            *requisitos.splitlines(),
        ],
        check=True,
        cwd=RAIZ,
        stdout=subprocess.DEVNULL,
    )


def podar(runtime: Path) -> int:
    """Remove os módulos do Qt que o app não usa. Devolve os bytes cortados."""
    site_packages = runtime / "Lib" / "site-packages"
    cortado = 0

    for pasta in PASTAS_FORA:
        alvo = site_packages / "PySide6" / Path(pasta)
        if alvo.is_dir():
            cortado += sum(f.stat().st_size for f in alvo.rglob("*") if f.is_file())
            shutil.rmtree(alvo)

    # A comparação é em minúsculas de propósito: o Qt escreve `Qt6WebEngine` no
    # nome da DLL e `qtwebengine` no nome do .pak, e a primeira versão desta
    # poda, que comparava sensível a maiúsculas, deixou 83 MB de recurso do
    # WebEngine para trás sem que nada quebrasse ou avisasse.
    fora = tuple(indesejado.lower() for indesejado in FORA)

    for arquivo in list(site_packages.rglob("*")):
        if not arquivo.is_file():
            continue
        if arquivo.suffix in (".pyi", ".lib", ".exp", ".prl"):
            cortado += arquivo.stat().st_size
            arquivo.unlink()
            continue
        if any(indesejado in arquivo.name.lower() for indesejado in fora):
            cortado += arquivo.stat().st_size
            arquivo.unlink()

    # Diretórios que ficaram vazios depois da poda.
    for pasta in sorted(site_packages.rglob("*"), key=lambda p: -len(p.parts)):
        if pasta.is_dir() and not any(pasta.iterdir()):
            pasta.rmdir()

    return cortado


def copiar_app(app: Path) -> None:
    """Copia o código e os desenhos, no layout que `assets_dir()` espera.

    `services.scene.assets_dir()` resolve `assets/` como `parents[2]` a partir
    de si mesmo, então `cantinho/` e `assets/` precisam ser irmãos. É o mesmo
    layout do repositório, e é por isso que aqui é cópia e não reorganização.
    """
    app.mkdir(parents=True, exist_ok=True)

    ignorar = shutil.ignore_patterns("__pycache__", "*.pyc", "*.db", "*.db-wal", "*.db-shm")
    shutil.copytree(RAIZ / "cantinho", app / "cantinho", ignore=ignorar, dirs_exist_ok=True)
    shutil.copytree(RAIZ / "assets", app / "assets", ignore=ignorar, dirs_exist_ok=True)


def escrever_lancadores(raiz_pacote: Path) -> None:
    """O .cmd e o atalho .lnk.

    O `.cmd` usa `pythonw.exe`, que é o interpretador sem console; o `start ""`
    faz o prompt devolver na hora em vez de ficar preso ao app. Ainda assim o
    `.cmd` pisca uma janela preta por um instante, e é por isso que o atalho
    existe: ele chama o `pythonw.exe` direto, sem intermediário nenhum.
    """
    (raiz_pacote / "Cantinho.cmd").write_text(
        "@echo off\r\n"
        "rem Abre o Cantinho com o pythonw.exe oficial, sem janela de console.\r\n"
        'start "" "%~dp0runtime\\pythonw.exe" -m cantinho.main %*\r\n',
        encoding="utf-8",
    )

    (raiz_pacote / "LEIA-ME.txt").write_text(LEIA_ME, encoding="utf-8")

    # O .lnk é um formato binário da shell; quem sabe escrever é o próprio
    # Windows. Sem pywin32 — o projeto não ganha dependência por causa de um
    # atalho.
    atalho = raiz_pacote / "Cantinho.lnk"
    icone = raiz_pacote / "app" / "assets" / "icon" / "cantinho.ico"
    script = f"""
$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{atalho}')
$s.TargetPath = '{raiz_pacote / "runtime" / "pythonw.exe"}'
$s.Arguments = '-m cantinho.main'
$s.WorkingDirectory = '{raiz_pacote / "app"}'
$s.IconLocation = '{icone}'
$s.Description = 'Cantinho'
$s.Save()
"""
    resultado = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0 or not atalho.is_file():
        log(f"  aviso: o atalho não pôde ser criado ({resultado.stderr.strip()[:120]})")
        log("  o Cantinho.cmd continua servindo")


def compactar(raiz_pacote: Path) -> Path:
    if ZIP_FINAL.exists():
        ZIP_FINAL.unlink()
    log(f"  compactando em {ZIP_FINAL.name}")
    with zipfile.ZipFile(ZIP_FINAL, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for arquivo in sorted(raiz_pacote.rglob("*")):
            if arquivo.is_file():
                z.write(arquivo, arquivo.relative_to(raiz_pacote.parent))
    return ZIP_FINAL


def tamanho(pasta: Path) -> float:
    return sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file()) / 1024 / 1024


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sem-zip", action="store_true", help="deixa só a pasta, sem compactar")
    args = parser.parse_args()

    raiz_pacote = DESTINO / "Cantinho"
    if DESTINO.exists():
        log(f"limpando {DESTINO.relative_to(RAIZ)}")
        shutil.rmtree(DESTINO)

    log("Python embeddable")
    montar_runtime(raiz_pacote / "runtime")

    log("PySide6")
    instalar_pyside(raiz_pacote / "runtime")

    log("podando o Qt")
    cortado = podar(raiz_pacote / "runtime")
    log(f"  {cortado / 1024 / 1024:.1f} MB removidos")

    log("app")
    copiar_app(raiz_pacote / "app")
    escrever_lancadores(raiz_pacote)

    log(f"pacote: {tamanho(raiz_pacote):.1f} MB em {raiz_pacote.relative_to(RAIZ)}")

    if not args.sem_zip:
        caminho = compactar(raiz_pacote)
        log(f"zip: {caminho.stat().st_size / 1024 / 1024:.1f} MB em {caminho.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
