from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


SIZES = [16, 32, 64, 128, 256, 512, 1024]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    assets_dir = root / "watermeal_agent" / "assets"
    source_svg = assets_dir / "app_icon.svg"
    build_dir = root / "build" / "icon.iconset"
    icns_path = assets_dir / "app_icon.icns"

    if shutil.which("iconutil") is None:
        print("iconutil not found. This script must run on macOS.", file=sys.stderr)
        return 1

    build_dir.parent.mkdir(parents=True, exist_ok=True)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    app = QGuiApplication.instance() or QGuiApplication([])
    renderer = QSvgRenderer(str(source_svg))
    if not renderer.isValid():
        print(f"Unable to load SVG: {source_svg}", file=sys.stderr)
        return 1

    for size in SIZES:
        _render_png(renderer, build_dir / f"icon_{size}x{size}.png", size)
        if size < 1024:
            _render_png(renderer, build_dir / f"icon_{size}x{size}@2x.png", size * 2)

    result = subprocess.run(
        ["iconutil", "-c", "icns", str(build_dir), "-o", str(icns_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    print(f"Built icon: {icns_path}")
    return 0


def _render_png(renderer: QSvgRenderer, path: Path, size: int) -> None:
    image = QImage(QSize(size, size), QImage.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    image.save(str(path))


if __name__ == "__main__":
    raise SystemExit(main())
