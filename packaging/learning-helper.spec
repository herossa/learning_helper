# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

ROOT = Path(SPECPATH).parent  # noqa: F821 - injetado pelo PyInstaller
SRC = ROOT / "src"
ICON = ROOT / "packaging" / "icons" / "learning-helper.ico"
VERSION_FILE = ROOT / "build" / "version_info.txt"

datas = [
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
    (
        str(SRC / "learning_helper" / "stats" / "app.py"),
        "learning_helper/stats",
    ),
]
binaries = []
hiddenimports = ["PIL._tkinter_finder"]
hiddenimports += collect_submodules("screeninfo")

# O Streamlit carrega o frontend, os schemas do Altair e os assets do pydeck
# como arquivos de dados. Sem eles o servidor sobe e a página fica em branco.
for package in ("streamlit", "altair", "pydeck", "watchdog"):
    options = {}
    if package == "streamlit":
        options["filter_submodules"] = (
            lambda name: not name.startswith("streamlit.testing")
        )
    package_datas, package_binaries, package_hiddenimports = collect_all(
        package, **options
    )
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

# Streamlit e Altair consultam a versão instalada via importlib.metadata.
for package in (
    "streamlit",
    "altair",
    "pydeck",
    "pandas",
    "numpy",
    "watchdog",
):
    try:
        datas += copy_metadata(package)
    except Exception:
        pass

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
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
