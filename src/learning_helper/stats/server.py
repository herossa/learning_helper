"""Servidor Streamlit das estatísticas (processo filho)."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

from learning_helper import lifecycle


def stats_app_path() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "learning_helper" / "stats" / "app.py"
    return Path(__file__).with_name("app.py")


def _exit_when_parent_dies(parent_pid: int) -> None:
    """Evita deixar o servidor órfão se a janela que o abriu for morta."""
    while True:
        time.sleep(1)
        if os.getppid() != parent_pid:
            os._exit(0)


def _exit_when_windows_parent_dies(parent_pid: int) -> None:
    """No Windows não há PDEATHSIG; espera o handle do processo pai."""
    import ctypes
    from ctypes import wintypes

    synchronize = 0x00100000
    infinite = 0xFFFFFFFF
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(synchronize, False, parent_pid)
    if not handle:
        os._exit(0)
    try:
        kernel32.WaitForSingleObject(handle, infinite)
    finally:
        kernel32.CloseHandle(handle)
    os._exit(0)


def _exit_on_quit_request() -> None:
    while True:
        if lifecycle.quit_requested():
            os._exit(0)
        time.sleep(0.5)


def _arm_parent_death_signal(parent_pid: int) -> None:
    """No Linux, pede ao kernel para encerrar o filho junto com o pai."""
    if sys.platform.startswith("linux"):
        try:
            import ctypes
            import signal

            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            pr_set_pdeathsig = 1
            libc.prctl(pr_set_pdeathsig, signal.SIGTERM, 0, 0, 0)
        except Exception:
            pass
    # Fecha a corrida em que o pai morreu entre o fork e o prctl.
    if os.getppid() != parent_pid:
        os._exit(0)


def run_streamlit(db_path: Path, port: int) -> int:
    # Em builds windowed (Windows) os streams podem ser None; o Streamlit e o
    # logging esperam arquivos de texto válidos.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    threading.Thread(target=_exit_on_quit_request, daemon=True).start()

    parent_pid = os.environ.get("LEARNING_HELPER_PARENT_PID")
    if parent_pid:
        try:
            parent = int(parent_pid)
        except ValueError:
            parent = 0
        if parent > 0:
            if sys.platform == "win32":
                threading.Thread(
                    target=_exit_when_windows_parent_dies,
                    args=(parent,),
                    daemon=True,
                ).start()
            else:
                _arm_parent_death_signal(parent)
                threading.Thread(
                    target=_exit_when_parent_dies,
                    args=(parent,),
                    daemon=True,
                ).start()

    try:
        from streamlit.web import cli as stcli
    except ImportError:
        print(
            "Streamlit não está instalado. Rode "
            "`uv sync` (ou instale a versão empacotada).",
            file=sys.stderr,
        )
        return 1

    os.environ["LEARNING_HELPER_DB"] = str(db_path)
    sys.argv = [
        "streamlit",
        "run",
        str(stats_app_path()),
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    try:
        result = stcli.main()
    except SystemExit as exc:
        return int(exc.code or 0)
    return int(result or 0)
