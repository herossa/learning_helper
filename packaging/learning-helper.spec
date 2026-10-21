# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent  # noqa: F821 - injetado pelo PyInstaller
SRC = ROOT / "src"
ICON = ROOT / "packaging" / "icons" / "learning-helper.ico"
VERSION_FILE = ROOT / "build" / "version_info.txt"

hiddenimports = ["PIL._tkinter_finder"]
hiddenimports += collect_submodules("screeninfo")

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        (
            str(SRC / "learning_helper" / "persistence" / "schema.sql"),
            "learning_helper/persistence",
        ),
        (
            str(SRC / "learning_helper" / "challenges" / "banks"),
            "learning_helper/challenges/banks",
        ),
        (
            str(SRC / "learning_helper" / "overlay" / "bathroom.png"),
            "learning_helper/overlay",
        ),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "_pytest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="learning-helper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if sys.platform == "win32" else None,
    version=(
        str(VERSION_FILE)
        if sys.platform == "win32" and VERSION_FILE.exists()
        else None
    ),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="learning-helper",
)
