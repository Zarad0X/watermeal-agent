from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path


APP_NAME = "Water Meal Agent"
LAUNCH_AGENT_LABEL = "com.zhanghan.watermealagent"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
LAUNCH_AGENT_PATH = LAUNCH_AGENTS_DIR / f"{LAUNCH_AGENT_LABEL}.plist"


def send_native_notification(title: str, message: str) -> None:
    script = (
        'display notification "{message}" with title "{title}"'
    ).format(
        title=_escape_applescript(title),
        message=_escape_applescript(message),
    )
    subprocess.run(
        ["osascript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )


def is_launch_agent_installed() -> bool:
    return LAUNCH_AGENT_PATH.exists()


def install_launch_agent(project_root: Path) -> None:
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = _launch_agent_payload(project_root)
    with LAUNCH_AGENT_PATH.open("wb") as handle:
        plistlib.dump(payload, handle)
    subprocess.run(["launchctl", "unload", str(LAUNCH_AGENT_PATH)], check=False)
    subprocess.run(["launchctl", "load", str(LAUNCH_AGENT_PATH)], check=False)


def remove_launch_agent() -> None:
    subprocess.run(["launchctl", "unload", str(LAUNCH_AGENT_PATH)], check=False)
    if LAUNCH_AGENT_PATH.exists():
        LAUNCH_AGENT_PATH.unlink()


def bundled_app_path() -> Path | None:
    executable = Path(sys.executable).resolve()
    for parent in executable.parents:
        if parent.suffix == ".app":
            return parent
    return None


def _launch_agent_payload(project_root: Path) -> dict:
    bundled_app = bundled_app_path()
    if bundled_app:
        program_arguments = [str(bundled_app / "Contents" / "MacOS" / APP_NAME)]
        working_directory = str(project_root)
    else:
        program_arguments = [sys.executable, "-m", "watermeal_agent"]
        working_directory = str(project_root)

    return {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": program_arguments,
        "RunAtLoad": True,
        "KeepAlive": False,
        "WorkingDirectory": working_directory,
        "ProcessType": "Interactive",
        "StandardOutPath": str(project_root / "launch-agent.out.log"),
        "StandardErrorPath": str(project_root / "launch-agent.err.log"),
    }


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
