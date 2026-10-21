import os
import subprocess
import sys
from pathlib import Path

from learning_helper import __version__
from learning_helper.app import parse_args

ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    if env:
        environment.update(env)
    return subprocess.run(
        [sys.executable, "-m", "learning_helper", *args],
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )


def test_version_flag() -> None:
    result = _run("--version")
    assert result.returncode == 0
    assert __version__ in result.stdout


def test_self_check_passes_without_touching_user_data(tmp_path: Path) -> None:
    result = _run(
        "--self-check",
        env={"XDG_DATA_HOME": str(tmp_path), "LOCALAPPDATA": str(tmp_path)},
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "learning_helper").exists()


def test_self_check_fails_when_bank_is_missing(monkeypatch) -> None:
    from learning_helper import app

    monkeypatch.setattr(app, "load_bank", lambda _name: [])
    assert app.self_check() == 1


def test_parse_args_accepts_new_flags() -> None:
    args = parse_args(["--self-check", "--enable-autostart", "--disable-autostart"])
    assert args.self_check is True
    assert args.enable_autostart is True
    assert args.disable_autostart is True
