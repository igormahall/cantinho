import sys
from pathlib import Path
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

app = QGuiApplication([])
falhou = False

for path in sorted(Path("assets").rglob("*.svg")):
    r = QSvgRenderer(str(path))
    if not r.isValid():
        print(f"FALHOU  {path}")
        falhou = True
        continue
    img = QImage(1100, 700, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    r.render(p)
    p.end()
    out = Path("build/svg_check") / f"{path.stem}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out))
    print(f"ok      {path}  ->  {out}")

sys.exit(1 if falhou else 0)
