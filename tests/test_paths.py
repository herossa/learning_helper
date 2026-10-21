from pathlib import Path

from learning_helper.persistence.db import data_dir, default_db_path


def test_linux_uses_xdg_data_home(tmp_path: Path) -> None:
    result = data_dir(platform="linux", env={"XDG_DATA_HOME": str(tmp_path)})
    assert result == tmp_path / "learning_helper"


def test_linux_falls_back_to_local_share(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    result = data_dir(platform="linux", env={})
    assert result == tmp_path / ".local" / "share" / "learning_helper"


def test_windows_uses_local_appdata(tmp_path: Path) -> None:
    result = data_dir(platform="win32", env={"LOCALAPPDATA": str(tmp_path)})
    assert result == tmp_path / "learning_helper"


def test_windows_falls_back_to_appdata_local(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    result = data_dir(platform="win32", env={})
    assert result == tmp_path / "AppData" / "Local" / "learning_helper"


def test_default_db_path_lives_in_the_app_directory() -> None:
    path = default_db_path()
    assert path.name == "learning_helper.db"
    assert path.parent.name == "learning_helper"
