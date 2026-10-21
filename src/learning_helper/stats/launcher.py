"""Abre as estatísticas no navegador e mantém o servidor enquanto a janela viver."""

from __future__ import annotations

import importlib.util
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from learning_helper.persistence.db import data_dir

HEALTH_TIMEOUT_SECONDS = 25
WINDOW_TITLE = "Learning Helper — Estatísticas"


def _executable_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "learning_helper"]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _is_healthy(port: int) -> bool:
    try:
        with urlopen(
            f"http://127.0.0.1:{port}/_stcore/health", timeout=1
        ) as response:
            return 200 <= response.status < 300
    except (URLError, OSError):
        return False


def _stop(child: subprocess.Popen) -> None:
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def _show_error(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(WINDOW_TITLE, message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def _serve_window(child: subprocess.Popen, url: str) -> None:
    import tkinter as tk

    root = tk.Tk()
    root.title(WINDOW_TITLE)
    root.geometry("540x210")
    root.resizable(False, False)

    tk.Label(
        root,
        text="As estatísticas estão abertas no navegador.",
        font=("Arial", 13, "bold"),
    ).pack(pady=(22, 6))
    tk.Label(root, text=url).pack()
    tk.Label(
        root,
        text="Feche esta janela para encerrar o servidor.",
        fg="#555555",
    ).pack(pady=(4, 10))
    tk.Button(
        root,
        text="Abrir no navegador",
        command=lambda: webbrowser.open(url),
        width=20,
    ).pack(pady=(0, 4))
    tk.Button(root, text="Encerrar", command=lambda: _stop_and_close(root, child)).pack()

    def stop() -> None:
        _stop_and_close(root, child)

    root.protocol("WM_DELETE_WINDOW", stop)
    root.mainloop()


def _stop_and_close(root, child: subprocess.Popen) -> None:
    _stop(child)
    root.destroy()


def run_stats(db_path: Path) -> int:
    if importlib.util.find_spec("streamlit") is None:
        _show_error(
            "Streamlit não está instalado. Rode `uv sync` no repositório ou "
            "use a versão empacotada."
        )
        return 1
    log_path = data_dir() / "stats.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    command = _executable_command() + [
        "--stats-server",
        "--stats-port",
        str(port),
        "--db",
        str(db_path),
    ]
    url = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment["LEARNING_HELPER_PARENT_PID"] = str(os.getpid())
    with log_path.open("a", encoding="utf-8") as log:
        child = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=environment,
            start_new_session=True,
        )
        deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
        ready = False
        while time.monotonic() < deadline:
            if child.poll() is not None:
                break
            if _is_healthy(port):
                ready = True
                break
            time.sleep(0.3)

        if not ready:
            _stop(child)
            _show_error(
                "Não foi possível abrir as estatísticas. "
                f"Veja o log em {log_path}."
            )
            return 1

        webbrowser.open(url)
        try:
            _serve_window(child, url)
        except Exception:
            # Sem Tk (ambiente headless): deixa o servidor no ar até Ctrl+C.
            print(f"Estatísticas em {url}. Pressione Ctrl+C para encerrar.")
            try:
                child.wait()
            except KeyboardInterrupt:
                pass
            finally:
                _stop(child)
    return 0
