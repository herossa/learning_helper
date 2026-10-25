import subprocess
from types import SimpleNamespace

import pytest

from learning_helper import power


def test_shutdown_command_per_platform() -> None:
    assert power.shutdown_command("linux") == [
        "systemctl",
        "poweroff",
        "--no-block",
    ]
    assert power.shutdown_command("win32") == ["shutdown", "/s", "/t", "0"]


def test_request_shutdown_runs_command(monkeypatch) -> None:
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(power.subprocess, "run", fake_run)

    power.request_shutdown("linux")

    assert calls[0][0] == ["systemctl", "poweroff", "--no-block"]
    assert calls[0][1]["check"] is False


def test_request_shutdown_reports_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        power.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="sem permissão",
        ),
    )

    with pytest.raises(power.ShutdownError, match="sem permissão"):
        power.request_shutdown("linux")


def test_request_shutdown_reports_missing_command(monkeypatch) -> None:
    def missing(*args, **kwargs):
        raise FileNotFoundError("systemctl")

    monkeypatch.setattr(power.subprocess, "run", missing)

    with pytest.raises(power.ShutdownError, match="systemctl"):
        power.request_shutdown("linux")


def test_request_shutdown_reports_timeout(monkeypatch) -> None:
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(["systemctl"], 15)

    monkeypatch.setattr(power.subprocess, "run", timeout)

    with pytest.raises(power.ShutdownError, match="demorou demais"):
        power.request_shutdown("linux")
