from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def tray_icon() -> QIcon:
    return QIcon(str(asset_path("tray_icon.svg")))


def app_icon() -> QIcon:
    return QIcon(str(asset_path("app_icon.svg")))


def asset_path(name: str) -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "watermeal_agent" / "assets" / name
    return Path(__file__).resolve().parent / "assets" / name
