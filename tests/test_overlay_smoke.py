import os
import random
import time
from datetime import datetime, timedelta, timezone

import pytest

if os.environ.get("RUN_GUI_TESTS") != "1":
    pytest.skip(
        "defina RUN_GUI_TESTS=1 para testar a interface (precisa de desktop)",
        allow_module_level=True,
    )

tkinter = pytest.importorskip("tkinter")
pytest.importorskip("customtkinter")

from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.config import RuntimeConfig
from learning_helper.overlay.main_window import OverlayApp
from learning_helper.persistence.db import Store


def test_overlay_builds_and_destroys(tmp_path) -> None:
    store = Store(tmp_path / "learning_helper.db")
    engine = AdaptiveEngine(store, rng=random.Random(0))
    try:
        try:
            app = OverlayApp(engine, RuntimeConfig(debug=True))
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        app.update()
        assert app.winfo_exists()
        app.destroy()
    finally:
        store.close()


def test_overlay_shows_and_hides_bathroom_reminder(tmp_path, monkeypatch) -> None:
    store = Store(tmp_path / "learning_helper.db")
    engine = AdaptiveEngine(store, rng=random.Random(0))
    profile = store.get_profile()
    profile.last_bathroom_reminder_at = datetime.now(timezone.utc) - timedelta(hours=1)
    store.save_profile(profile)
    try:
        # Sem desafio na tela: o lembrete (vencido) deve aparecer no agendador.
        monkeypatch.setattr(OverlayApp, "_show_challenge", lambda self: None)
        try:
            app = OverlayApp(engine, RuntimeConfig(debug=True))
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        deadline = time.monotonic() + 5
        while not app._bathroom_visible and time.monotonic() < deadline:
            app.update()
            time.sleep(0.05)
        assert app._bathroom_visible is True
        assert engine.profile().last_bathroom_reminder_at is not None
        app._hide_bathroom()
        app.update()
        assert app._bathroom_visible is False
        app.destroy()
    finally:
        store.close()

