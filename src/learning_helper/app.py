from __future__ import annotations

import argparse
import sys

from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.config import RuntimeConfig
from learning_helper.persistence.db import Store, default_db_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Learning helper")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Intervalo curto e botão de fechar no overlay.",
    )
    parser.add_argument(
        "--db",
        help="Caminho do SQLite (padrão: diretório de dados do usuário).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    store = Store(args.db or default_db_path())
    engine = AdaptiveEngine(store)
    config = RuntimeConfig(debug=args.debug)
    from learning_helper.overlay.main_window import OverlayApp

    app = OverlayApp(engine, config)
    app.mainloop()
