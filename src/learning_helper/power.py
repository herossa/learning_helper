"""Desligamento do computador por plataforma."""

from __future__ import annotations

import subprocess
import sys


class ShutdownError(RuntimeError):
    """Falha ao solicitar o desligamento do computador."""


SHUTDOWN_TIMEOUT_SECONDS = 15


def shutdown_command(platform: str | None = None) -> list[str]:
    if (platform or sys.platform) == "win32":
        return ["shutdown", "/s", "/t", "0"]
    return ["systemctl", "poweroff", "--no-block"]


def request_shutdown(platform: str | None = None) -> None:
    command = shutdown_command(platform)
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=SHUTDOWN_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ShutdownError(
            "O comando de desligamento demorou demais para responder."
        ) from exc
    except OSError as exc:
        raise ShutdownError(f"Não foi possível desligar: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        message = f"O desligamento falhou (código {result.returncode})."
        if detail:
            message = f"{message} {detail}"
        raise ShutdownError(message)
