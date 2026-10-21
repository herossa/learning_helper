from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

from learning_helper import __version__
from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.challenges.banks import load_bank
from learning_helper.config import RuntimeConfig
from learning_helper.persistence.db import (
    Store,
    data_dir,
    default_db_path,
    schema_sql,
)
from learning_helper.single_instance import SingleInstance

LOGGER = logging.getLogger(__name__)
LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Learning helper")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Intervalo curto e botão de fechar no overlay.",
    )
    parser.add_argument(
        "--db",
        help="Caminho do SQLite (padrão: diretório de dados do usuário).",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Valida os recursos empacotados e sai (usado pelo build).",
    )
    parser.add_argument(
        "--enable-autostart",
        action="store_true",
        help="Inicia junto com o usuário atual (Linux).",
    )
    parser.add_argument(
        "--disable-autostart",
        action="store_true",
        help="Remove a inicialização automática do usuário (Linux).",
    )
    return parser.parse_args(argv)


def setup_logging() -> Path:
    path = data_dir() / "app.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        return path
    handler = RotatingFileHandler(
        path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    return path


def self_check() -> int:
    try:
        if not schema_sql().strip():
            raise RuntimeError("schema.sql vazio")
        for name in ("questions", "reading"):
            if not load_bank(name):
                raise RuntimeError(f"banco {name}.json vazio")
        with tempfile.TemporaryDirectory(prefix="learning-helper-check-") as tmp:
            store = Store(Path(tmp) / "check.db")
            try:
                if store.count_attempts() != 0:
                    raise RuntimeError("banco de verificação inesperado")
            finally:
                store.close()
    except Exception:
        LOGGER.exception("Self-check falhou")
        return 1
    return 0


def _handle_autostart(args: argparse.Namespace) -> int | None:
    from learning_helper import autostart

    if not (args.enable_autostart or args.disable_autostart):
        return None
    if not autostart.SUPPORTED:
        print(
            "No Windows o autostart é gerenciado pelo instalador.",
            file=sys.stderr,
        )
        return 0
    if args.enable_autostart:
        path = autostart.enable_autostart()
        print(f"Autostart habilitado em {path}")
    if args.disable_autostart:
        removed = autostart.disable_autostart()
        print("Autostart removido." if removed else "Autostart não estava habilitado.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.self_check:
        return self_check()

    autostart_result = _handle_autostart(args)
    if autostart_result is not None:
        return autostart_result

    log_path = setup_logging()
    LOGGER.info("Iniciando learning-helper %s (log: %s)", __version__, log_path)

    lock = SingleInstance(data_dir() / "app.lock")
    if not lock.acquire():
        LOGGER.warning("Outra instância já está em execução; encerrando esta.")
        return 0
    try:
        return _run(args)
    except Exception:
        LOGGER.exception("Falha inesperada")
        return 1
    finally:
        lock.release()


def _run(args: argparse.Namespace) -> int:
    store = Store(Path(args.db) if args.db else default_db_path())
    try:
        engine = AdaptiveEngine(store)
        config = RuntimeConfig(debug=args.debug)
        from learning_helper.overlay.main_window import OverlayApp

        app = OverlayApp(engine, config)
        app.mainloop()
    finally:
        store.close()
    return 0
