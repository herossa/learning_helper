import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "packaging" / "make_update_manifest.py"


def _module():
    spec = importlib.util.spec_from_file_location("make_update_manifest", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: bytes) -> None:
    path.write_bytes(content)


def test_build_manifest_can_select_windows_only(tmp_path: Path) -> None:
    module = _module()
    setup = tmp_path / "LearningHelper-0.9.0-Setup.exe"
    _write(setup, b"setup")

    manifest = module.build_manifest(
        "0.9.0",
        tmp_path,
        base_url="http://127.0.0.1:8765",
        asset_keys=["windows_setup"],
    )

    assert manifest["version"] == "0.9.0"
    assert list(manifest["assets"]) == ["windows_setup"]
    asset = manifest["assets"]["windows_setup"]
    assert asset["name"] == setup.name
    assert asset["url"] == f"http://127.0.0.1:8765/{setup.name}"
    assert asset["sha256"] == hashlib.sha256(b"setup").hexdigest()


def test_build_manifest_reports_missing_selected_asset(tmp_path: Path) -> None:
    module = _module()

    with pytest.raises(SystemExit, match="Arquivos ausentes"):
        module.build_manifest(
            "0.9.0",
            tmp_path,
            base_url="http://127.0.0.1:8765",
            asset_keys=["windows_setup"],
        )


def test_build_manifest_rejects_empty_selection(tmp_path: Path) -> None:
    module = _module()

    with pytest.raises(SystemExit, match="Nenhum asset"):
        module.build_manifest(
            "0.9.0",
            tmp_path,
            base_url="http://127.0.0.1:8765",
            asset_keys=[],
        )
