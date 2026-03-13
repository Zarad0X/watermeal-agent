from __future__ import annotations

import json
from pathlib import Path

from .models import AppConfig, AppState


APP_DIR = Path.home() / "Library" / "Application Support" / "WaterMealAgent"
CONFIG_PATH = APP_DIR / "config.json"
STATE_PATH = APP_DIR / "state.json"
LOG_PATH = APP_DIR / "app.log"


class JsonStore:
    def __init__(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> AppConfig:
        return AppConfig.from_dict(self._read_json(CONFIG_PATH))

    def save_config(self, config: AppConfig) -> None:
        self._write_json(CONFIG_PATH, config.to_dict())

    def load_state(self) -> AppState:
        return AppState.from_dict(self._read_json(STATE_PATH))

    def save_state(self, state: AppState) -> None:
        self._write_json(STATE_PATH, state.to_dict())

    def _read_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_json(self, path: Path, payload: dict) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
