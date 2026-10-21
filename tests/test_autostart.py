import sys
from pathlib import Path

import pytest

from learning_helper import autostart

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="autostart é gerenciado pelo instalador no Windows"
)


def test_enable_and_disable_use_user_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    path = autostart.enable_autostart()
    assert path == tmp_path / ".config" / "autostart" / "learning-helper.desktop"
    content = path.read_text(encoding="utf-8")
    assert "Type=Application" in content
    assert "Exec=" in content
    assert "Terminal=false" in content

    assert autostart.disable_autostart() is True
    assert not path.exists()
    assert autostart.disable_autostart() is False


def test_xdg_config_home_takes_precedence(tmp_path: Path) -> None:
    path = autostart.autostart_path(env={"XDG_CONFIG_HOME": str(tmp_path)})
    assert path == tmp_path / "autostart" / "learning-helper.desktop"


def test_desktop_entry_quotes_paths_with_spaces() -> None:
    entry = autostart.desktop_entry(["/opt/My App/learning-helper"])
    assert 'Exec="/opt/My App/learning-helper"' in entry


def test_desktop_entry_keeps_module_command() -> None:
    entry = autostart.desktop_entry(["/usr/bin/python3", "-m", "learning_helper"])
    assert "Exec=/usr/bin/python3 -m learning_helper" in entry
