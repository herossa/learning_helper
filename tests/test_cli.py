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


def test_parse_args_accepts_bathroom_flags() -> None:
    args = parse_args(["--enable-bathroom-reminder", "--disable-bathroom-reminder"])
    assert args.enable_bathroom_reminder is True
    assert args.disable_bathroom_reminder is True


def test_bathroom_flags_persist_preference(tmp_path: Path) -> None:
    db_path = tmp_path / "learning_helper.db"
    env = {"XDG_DATA_HOME": str(tmp_path), "LOCALAPPDATA": str(tmp_path)}

    disabled = _run("--disable-bathroom-reminder", "--db", str(db_path), env=env)
    assert disabled.returncode == 0, disabled.stderr
    assert "desabilitado" in disabled.stdout

    from learning_helper.persistence.db import Store

    store = Store(db_path)
    try:
        assert store.get_settings().bathroom_reminder_enabled is False
    finally:
        store.close()

    enabled = _run("--enable-bathroom-reminder", "--db", str(db_path), env=env)
    assert enabled.returncode == 0, enabled.stderr
    assert "habilitado" in enabled.stdout

    store = Store(db_path)
    try:
        assert store.get_settings().bathroom_reminder_enabled is True
    finally:
        store.close()



def test_parse_args_accepts_settings() -> None:
    args = parse_args(["--settings"])
    assert args.settings is True
    assert args.first_run is False


def test_run_opens_settings_on_first_run(tmp_path, monkeypatch) -> None:
    import argparse

    from learning_helper import app

    calls = []

    def fake_first_run(store):
        calls.append("settings")
        store.complete_onboarding()

    class FakeOverlay:
        def __init__(self, engine, config) -> None:
            calls.append(("overlay", config.debug))

        def mainloop(self) -> None:
            calls.append("mainloop")

    monkeypatch.setattr(app, "_run_first_run_settings", fake_first_run)
    monkeypatch.setattr(
        "learning_helper.overlay.main_window.OverlayApp",
        FakeOverlay,
    )
    db_path = tmp_path / "learning_helper.db"
    result = app._run(argparse.Namespace(db=str(db_path), debug=False))
    assert result == 0
    assert calls == ["settings", ("overlay", False), "mainloop"]


def test_run_skips_settings_when_onboarding_is_complete(tmp_path, monkeypatch) -> None:
    import argparse

    from learning_helper import app
    from learning_helper.persistence.db import Store

    db_path = tmp_path / "learning_helper.db"
    store = Store(db_path)
    store.complete_onboarding()
    store.close()

    calls = []

    def fake_first_run(store):
        calls.append("settings")

    class FakeOverlay:
        def __init__(self, engine, config) -> None:
            pass

        def mainloop(self) -> None:
            calls.append("mainloop")

    monkeypatch.setattr(app, "_run_first_run_settings", fake_first_run)
    monkeypatch.setattr(
        "learning_helper.overlay.main_window.OverlayApp",
        FakeOverlay,
    )
    result = app._run(argparse.Namespace(db=str(db_path), debug=False))
    assert result == 0
    assert calls == ["mainloop"]


def test_run_settings_passes_first_run_flag(tmp_path, monkeypatch) -> None:
    import argparse

    from learning_helper import app

    calls = []

    def fake_settings(store, *, first_run=False):
        calls.append(first_run)
        return 0

    monkeypatch.setattr(
        "learning_helper.overlay.settings_window.run_settings_window",
        fake_settings,
    )
    result = app._run_settings(
        argparse.Namespace(
            db=str(tmp_path / "learning_helper.db"),
            first_run=True,
        )
    )
    assert result == 0
    assert calls == [True]


def test_first_run_helper_spawns_settings_and_falls_back_to_defaults(
    tmp_path, monkeypatch
) -> None:
    from learning_helper import app
    from learning_helper.persistence.db import Store

    commands = []

    class Result:
        returncode = 1

    def fake_run(command, check=False):
        commands.append((command, check))
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr(
        "learning_helper.autostart.executable_command",
        lambda: ["/opt/learning-helper", "-m", "learning_helper"],
    )

    store = Store(tmp_path / "learning_helper.db")
    try:
        app._run_first_run_settings(store)
        assert store.onboarding_completed() is True
    finally:
        store.close()

    assert len(commands) == 1
    command, check = commands[0]
    assert check is False
    assert command[:5] == [
        "/opt/learning-helper",
        "-m",
        "learning_helper",
        "--settings",
        "--first-run",
    ]
    assert command[-2:] == ["--db", str(tmp_path / "learning_helper.db")]


def test_first_run_child_changes_are_visible_to_parent(tmp_path, monkeypatch) -> None:
    import sys

    from learning_helper import app
    from learning_helper.persistence.db import Store

    db_path = tmp_path / "learning_helper.db"
    child = tmp_path / "fake_settings.py"
    child.write_text(
        """
import sys
from pathlib import Path
from learning_helper.persistence.db import Store
from learning_helper.settings import Settings

db = Path(sys.argv[sys.argv.index("--db") + 1])
store = Store(db)
store.save_settings(
    Settings(
        initial_interval_seconds=240,
        min_interval_seconds=60,
        max_interval_seconds=300,
    )
)
profile = store.get_profile()
profile.interval_seconds = 240
store.save_profile(profile)
store.complete_onboarding()
store.close()
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "learning_helper.autostart.executable_command",
        lambda: [sys.executable, str(child)],
    )
    store = Store(db_path)
    try:
        app._run_first_run_settings(store)
        assert store.onboarding_completed() is True
        assert store.get_settings().initial_interval_seconds == 240
        assert store.get_profile().interval_seconds == 240
    finally:
        store.close()
