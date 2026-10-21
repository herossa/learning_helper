"""Solicitação de encerramento entre processos do Learning Helper.

O pedido é um arquivo no diretório de dados. Cada processo em execução
(overlay, configurações, estatísticas) verifica o arquivo periodicamente e
encerra. O arquivo não é consumido por quem lê, para que todos vejam o pedido;
ele expira sozinho para não afetar uma inicialização futura.
"""

from __future__ import annotations

import time
from pathlib import Path

from learning_helper.persistence.db import data_dir

QUIT_FILE_NAME = "quit.request"
QUIT_MAX_AGE_SECONDS = 30.0


def quit_path(base: Path | None = None) -> Path:
    return (Path(base) if base is not None else data_dir()) / QUIT_FILE_NAME


def request_quit(base: Path | None = None) -> Path:
    path = quit_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(time.time()), encoding="utf-8")
    return path


def quit_requested(
    base: Path | None = None,
    *,
    max_age: float = QUIT_MAX_AGE_SECONDS,
) -> bool:
    path = quit_path(base)
    try:
        age = time.time() - path.stat().st_mtime
    except FileNotFoundError:
        return False
    if age > max_age:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return False
    return True


def clear_quit_request(base: Path | None = None) -> None:
    """Remove um pedido antigo ao iniciar um processo novo."""
    try:
        quit_path(base).unlink()
    except FileNotFoundError:
        pass
