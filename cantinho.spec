# -*- mode: python ; coding: utf-8 -*-
"""Build portable, onedir.

Roda de pendrive, sem instalação e sem admin — que é a restrição da máquina
onde ele precisa abrir. Por isso onedir e não onefile: onefile desempacota em
%TEMP% a cada abertura, o que é lento e costuma esbarrar em política de
execução.

O build é feito em cada plataforma separadamente. Este spec serve aos dois, mas
o artefato de um não serve ao outro.

    pyinstaller cantinho.spec --noconfirm
"""

import sys

# Os QML e os SVG são lidos do disco em runtime, não importados. Precisam vir
# como dados, e no mesmo layout relativo que `services.scene.assets_dir` e
# `main._ui_dir` esperam encontrar dentro do _MEIPASS.
datas = [
    ("assets", "assets"),
    ("cantinho/ui", "cantinho/ui"),
]

hiddenimports = [
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtSvg",
    "PySide6.QtMultimedia",
    "PySide6.QtWidgets",
    # QLocalServer, usado pela trava de instância única. Nada de rede sai da
    # máquina: é named pipe local.
    "PySide6.QtNetwork",
]

a = Analysis(
    ["cantinho/main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # Módulos Qt que o app não usa. Cortar aqui é o que mantém a pasta em um
    # tamanho razoável para carregar em pendrive.
    excludes=[
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
        "tkinter",
        "unittest",
        "pydoc",
        "pytest",
    ],
    noarchive=False,
)

# Excluir o módulo Python não basta: o PyInstaller recolhe as DLL do Qt como
# dependência binária, por fora da lista de excludes. Sem este filtro,
# Qt6WebEngineCore.dll sozinha põe 196 MB numa pasta que precisa caber em
# pendrive. Nada aqui é importado pelo app.
_FORA = (
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
    "Qt6Quick3D",
)


def _manter(entrada):
    nome = entrada[0]
    return not any(indesejado in nome for indesejado in _FORA)


a.binaries = [b for b in a.binaries if _manter(b)]
a.datas = [d for d in a.datas if _manter(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Cantinho",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Sem console: é um app de ambiente, não uma ferramenta de terminal.
    console=False,
    # Sem isto o executável sai com o ícone padrão do PyInstaller.
    icon="assets/icon/cantinho.ico",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Cantinho",
)
