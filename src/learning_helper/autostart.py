from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path

AUTOSTART_FILE_NAME = "learning-helper.desktop"
SUPPORTED = sys.platform != "win32"


def autostart_path(env: Mapping[str, str] | None = None) -> Path:
    environment = os.environ if env is None else env
    config_home = environment.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home) / "autostart" / AUTOSTART_FILE_NAME


def executable_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.argv[0]).resolve())]
    return [sys.executable, "-m", "learning_helper"]


def _exec_value(command: list[str]) -> str:
    return " ".join(f'"{part}"' if " " in part else part for part in command)


def desktop_entry(command: list[str]) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Learning Helper\n"
        "Comment=Desafios curtos para aprender\n"
        f"Exec={_exec_value(command)}\n"
        "Icon=learning-helper\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def enable_autostart(path: Path | None = None) -> Path:
    target = path or autostart_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(desktop_entry(executable_command()), encoding="utf-8")
    return target


def disable_autostart(path: Path | None = None) -> bool:
    target = path or autostart_path()
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True


def is_enabled(path: Path | None = None) -> bool:
    return (path or autostart_path()).is_file()
