from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from dataclasses import replace
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
        "--settings",
        action="store_true",
        help="Abre a tela de configuração e sai.",
    )
    parser.add_argument(
        "--first-run",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Abre as estatísticas no navegador.",
    )
    parser.add_argument(
        "--check-updates",
        action="store_true",
        help="Verifica se há uma versão nova e sai.",
    )
    parser.add_argument(
        "--quit",
        action="store_true",
        help="Encerra uma instância em execução.",
    )
    parser.add_argument(
        "--stats-server",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--stats-port",
        type=int,
        default=8501,
        help=argparse.SUPPRESS,
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
    parser.add_argument(
        "--enable-bathroom-reminder",
        action="store_true",
        help="Liga o lembrete de banheiro (padrão: ligado).",
    )
    parser.add_argument(
        "--disable-bathroom-reminder",
        action="store_true",
        help="Desliga o lembrete de banheiro.",
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
        from learning_helper.overlay.images import load_bathroom_image

        image = load_bathroom_image()
        if image.width <= 0 or image.height <= 0:
            raise RuntimeError("bathroom.png inválido")

        import altair
        import pandas
        import streamlit

        static = Path(streamlit.__file__).with_name("static")
        if not static.is_dir():
            raise RuntimeError("assets estáticos do Streamlit não encontrados")
        # O painel usa pandas e o Streamlit usa Altair para os gráficos; o
        # schema do Altair é um arquivo de dados que o PyInstaller pode perder.
        altair.Chart(
            pandas.DataFrame({"x": [1], "y": [2]})
        ).mark_bar().encode(x="x", y="y").to_dict()
        from learning_helper.stats.server import stats_app_path

        if not stats_app_path().is_file():
            raise RuntimeError("app.py das estatísticas não encontrado")

        # O painel importa este módulo ao rodar dentro do Streamlit; conferir
        # aqui garante que o PyInstaller não o deixou de fora do bundle.
        from learning_helper.stats import data as stats_data

        if not callable(stats_data.load_attempts):
            raise RuntimeError("módulo de dados das estatísticas incompleto")

        # O atualizador é importado em tempo de execução pelo app e pelas
        # configurações; validar aqui evita descobrir módulos faltando só no
        # build empacotado.
        from learning_helper.updates import client, install, manifest, service, state

        if not callable(client.fetch_manifest) or not callable(install.apply_pending):
            raise RuntimeError("módulo de atualização incompleto")
        if not callable(state.load_state) or not callable(service.prepare_update):
            raise RuntimeError("módulo de atualização incompleto")
        if not manifest.is_newer("0.0.2", "0.0.1"):
            raise RuntimeError("comparação de versões do atualizador falhou")

        with tempfile.TemporaryDirectory(prefix="learning-helper-check-") as tmp:
            store = Store(Path(tmp) / "check.db")
            try:
                if store.count_attempts() != 0:
                    raise RuntimeError("banco de verificação inesperado")
                if store.onboarding_completed():
                    raise RuntimeError("banco novo já estava configurado")
            finally:
                store.close()
    except Exception:
        LOGGER.exception("Self-check falhou")
        return 1
    return 0


def _db_path(args: argparse.Namespace) -> Path:
    return Path(args.db) if args.db else default_db_path()


def _check_updates() -> int:
    from learning_helper.updates.client import fetch_manifest
    from learning_helper.updates.install import select_asset
    from learning_helper.updates.manifest import UpdateError, is_newer

    try:
        release = fetch_manifest()
    except UpdateError as exc:
        print(f"Não foi possível verificar atualizações: {exc}", file=sys.stderr)
        return 1
    if not is_newer(release.version, __version__):
        print(f"Você está na versão mais recente ({__version__}).")
        return 0
    print(f"Nova versão disponível: {release.version} (atual {__version__}).")
    selection = select_asset(release)
    if selection is None:
        print("Atualização automática não disponível nesta execução.")
    else:
        key, asset = selection
        print(f"Pacote: {asset.name} ({key}).")
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


def _handle_bathroom_preference(args: argparse.Namespace) -> int | None:
    if not (args.enable_bathroom_reminder or args.disable_bathroom_reminder):
        return None
    store = Store(_db_path(args))
    enabled = args.enable_bathroom_reminder and not args.disable_bathroom_reminder
    try:
        settings = replace(
            store.get_settings(), bathroom_reminder_enabled=enabled
        )
        store.save_settings(settings)
    finally:
        store.close()
    if enabled:
        print("Lembrete de banheiro habilitado.")
    else:
        print("Lembrete de banheiro desabilitado.")
    return 0


def _run_settings(args: argparse.Namespace) -> int:
    store = Store(_db_path(args))
    try:
        from learning_helper.overlay.settings_window import run_settings_window

        return run_settings_window(
            store, first_run=bool(getattr(args, "first_run", False))
        )
    finally:
        store.close()


def _run_first_run_settings(store: Store) -> None:
    """Abre a configuração inicial em outro processo.

    O Tk/customtkinter mantém callbacks globais depois que uma janela é
    destruída; separar o processo evita que a tela de configuração interfira
    na janela do overlay (escala/fontes).
    """
    import subprocess

    from learning_helper import autostart

    command = autostart.executable_command() + [
        "--settings",
        "--first-run",
        "--db",
        str(store.db_path),
    ]
    try:
        result = subprocess.run(command, check=False)
    except OSError:
        LOGGER.exception("Não foi possível abrir a configuração inicial")
        result = None
    if result is not None and result.returncode != 0:
        LOGGER.warning(
            "Tela de configuração inicial terminou com código %s",
            result.returncode,
        )
    if not store.onboarding_completed():
        LOGGER.warning("Configuração inicial não concluída; usando padrões.")
        store.complete_onboarding()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.self_check:
        return self_check()

    from learning_helper import lifecycle

    if args.check_updates:
        return _check_updates()
    if args.quit:
        path = lifecycle.request_quit()
        print(f"Solicitação de encerramento enviada ({path}).")
        return 0

    # Um pedido antigo não deve encerrar um processo que está nascendo agora.
    lifecycle.clear_quit_request()

    if args.stats_server:
        from learning_helper.stats.server import run_streamlit

        return run_streamlit(_db_path(args), args.stats_port)
    if args.stats:
        from learning_helper.stats.launcher import run_stats

        return run_stats(_db_path(args))

    autostart_result = _handle_autostart(args)
    if autostart_result is not None:
        return autostart_result

    bathroom_result = _handle_bathroom_preference(args)
    if bathroom_result is not None:
        return bathroom_result

    if args.settings:
        return _run_settings(args)

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
    store = Store(_db_path(args))
    try:
        if not store.onboarding_completed():
            _run_first_run_settings(store)

        update_service = None
        settings = store.get_settings()
        if getattr(sys, "frozen", False):
            from learning_helper.updates.service import UpdateService

            update_service = UpdateService(__version__, data_dir())
            if (
                settings.update_check_on_startup
                and not os.environ.get("LEARNING_HELPER_NO_UPDATE")
            ):
                update_service.start()

        engine = AdaptiveEngine(store)
        config = RuntimeConfig(debug=args.debug)
        from learning_helper.overlay.main_window import OverlayApp

        if update_service is None:
            app = OverlayApp(engine, config)
        else:
            app = OverlayApp(engine, config, update_service=update_service)
        app.mainloop()
    finally:
        store.close()
    return 0
