#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 - <<'PY'
from pathlib import Path
from watermeal_agent.macos import install_launch_agent

install_launch_agent(Path.cwd())
print("Launch agent installed.")
PY
