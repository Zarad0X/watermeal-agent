#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 - <<'PY'
from watermeal_agent.macos import remove_launch_agent

remove_launch_agent()
print("Launch agent removed.")
PY
