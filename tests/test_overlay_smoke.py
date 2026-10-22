import gc
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


@pytest.fixture(autouse=True)
def _collect_gui_garbage():
    yield
    gc.collect()


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



class _FastConfig(RuntimeConfig):
    def delay_ms(self, adaptive_seconds: int, minimum: int, maximum: int) -> int:
        return 300


def test_overlay_does_not_show_challenge_immediately(tmp_path) -> None:
    store = Store(tmp_path / "learning_helper.db")
    engine = AdaptiveEngine(store, rng=random.Random(0))
    try:
        try:
            app = OverlayApp(engine, _FastConfig())
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        app.update()
        assert app._showing is False
        assert app._job is not None

        deadline = time.monotonic() + 3
        while not app._showing and time.monotonic() < deadline:
            app.update()
            time.sleep(0.02)
        assert app._showing is True
        app.destroy()
    finally:
        store.close()


def test_challenge_panel_text_mode_submits_typed_answer() -> None:
    import customtkinter

    from learning_helper.adaptive.models import ChallengeSpec
    from learning_helper.overlay.host import ChallengePanel

    try:
        root = customtkinter.CTk()
    except tkinter.TclError:
        pytest.skip("sem display disponível")
    root.withdraw()
    answers: list[str] = []
    spec = ChallengeSpec(
        module_id="compare",
        level=1,
        prompt="Qual dos dois números a seguir é maior?\n\n7  ou  3",
        choices=(),
        correct_id="7",
        input_mode="text",
    )
    panel = ChallengePanel(
        root,
        spec,
        on_answer=lambda _spec, given: answers.append(given),
        feedback_ms=10,
    )
    panel.pack()
    root.update()

    assert panel._entry is not None
    panel._submit_text()
    assert answers == []
    assert panel._hint is not None
    assert panel._hint.cget("text") == "Digite um número."

    panel._entry.insert(0, "abc")
    panel._submit_text()
    assert answers == []
    assert panel._hint.cget("text") == "Digite apenas o número."

    panel._entry.delete(0, "end")
    panel._entry.insert(0, " 07 ")
    panel._submit_text()
    assert panel._status.cget("text") == "Certo!"

    deadline = time.monotonic() + 2
    while not answers and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert answers == ["07"]
    assert panel._entry.cget("state") == "disabled"
    root.destroy()


def test_settings_window_saves_and_completes_onboarding(tmp_path) -> None:
    from learning_helper.overlay.settings_window import SettingsWindow

    store = Store(tmp_path / "learning_helper.db")
    try:
        try:
            window = SettingsWindow(store, first_run=True)
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        window._vars["initial"].set("4")
        window._save()
        assert store.onboarding_completed() is True
        assert store.get_settings().initial_interval_seconds == 240
        assert store.get_profile().interval_seconds == 240
    finally:
        store.close()


def test_settings_window_close_uses_defaults_on_first_run(tmp_path) -> None:
    from learning_helper.overlay.settings_window import SettingsWindow
    from learning_helper.settings import Settings

    store = Store(tmp_path / "learning_helper.db")
    try:
        try:
            window = SettingsWindow(store, first_run=True)
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        window._vars["initial"].set("9")
        window._on_close()
        assert store.onboarding_completed() is True
        assert store.get_settings().initial_interval_seconds == (
            Settings().initial_interval_seconds
        )
        assert store.get_profile().interval_seconds == (
            Settings().initial_interval_seconds
        )
    finally:
        store.close()


def test_settings_window_cancel_does_not_save_in_normal_mode(tmp_path) -> None:
    from learning_helper.overlay.settings_window import SettingsWindow

    store = Store(tmp_path / "learning_helper.db")
    store.save_settings(store.get_settings())
    try:
        try:
            window = SettingsWindow(store, first_run=False)
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        window._vars["initial"].set("4")
        window._on_close()
        assert store.get_settings().initial_interval_seconds == 180
    finally:
        store.close()


def test_settings_window_reports_validation_errors(tmp_path) -> None:
    from learning_helper.overlay.settings_window import SettingsWindow

    store = Store(tmp_path / "learning_helper.db")
    try:
        try:
            window = SettingsWindow(store, first_run=True)
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        window._vars["initial"].set("99")
        window._save()
        assert window.winfo_exists()
        assert window._status.cget("text")
        assert store.get_settings().initial_interval_seconds == 180
        window.destroy()
    finally:
        store.close()


def test_settings_window_does_not_change_current_interval_later(tmp_path) -> None:
    from learning_helper.overlay.settings_window import SettingsWindow

    store = Store(tmp_path / "learning_helper.db")
    store.complete_onboarding()
    profile = store.get_profile()
    profile.interval_seconds = 300
    store.save_profile(profile)
    try:
        try:
            window = SettingsWindow(store, first_run=False)
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        window._vars["initial"].set("4")
        window._save()
        assert store.get_settings().initial_interval_seconds == 240
        assert store.get_profile().interval_seconds == 300
    finally:
        store.close()
