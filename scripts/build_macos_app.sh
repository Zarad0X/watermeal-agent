#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing virtualenv python at $PYTHON_BIN" >&2
  exit 1
fi

"$PYTHON_BIN" scripts/build_iconset.py

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --windowed \
  --name "Water Meal Agent" \
  --clean \
  --add-data "watermeal_agent:watermeal_agent" \
  --icon "watermeal_agent/assets/app_icon.icns" \
  --hidden-import "PySide6.QtSvg" \
  run_agent.py

echo "Built app at: $ROOT_DIR/dist/Water Meal Agent.app"
