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
from learning_helper.security import hash_password


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
        answer_delay_ms=0,
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


def test_challenge_panel_accepts_any_correct_color() -> None:
    import customtkinter

    from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
    from learning_helper.overlay.host import ChallengePanel

    try:
        root = customtkinter.CTk()
    except tkinter.TclError:
        pytest.skip("sem display disponível")
    root.withdraw()
    answers: list[str] = []
    spec = ChallengeSpec(
        module_id="not_colors",
        level=1,
        prompt="Clique na cor que não é o verde.",
        choices=(
            ChallengeChoice(id="green", label="Verde"),
            ChallengeChoice(id="blue", label="Azul"),
            ChallengeChoice(id="red", label="Vermelho"),
        ),
        correct_id="blue",
        correct_ids=("blue", "red"),
        correct_summary="qualquer cor diferente de Verde",
    )
    panel = ChallengePanel(
        root,
        spec,
        on_answer=lambda _spec, given: answers.append(given),
        feedback_ms=10,
        answer_delay_ms=0,
    )
    panel.pack()
    root.update()

    panel._choose("red")
    assert panel._status.cget("text") == "Certo!"

    deadline = time.monotonic() + 2
    while not answers and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert answers == ["red"]
    root.destroy()


def test_challenge_panel_keeps_answers_disabled_until_delay() -> None:
    import customtkinter

    from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
    from learning_helper.overlay.host import GUIDANCE_TEXT, ChallengePanel

    try:
        root = customtkinter.CTk()
    except tkinter.TclError:
        pytest.skip("sem display disponível")
    root.withdraw()
    answers: list[str] = []
    spec = ChallengeSpec(
        module_id="colors",
        level=1,
        prompt="Clique na cor azul.",
        choices=(
            ChallengeChoice(id="red", label="Vermelho"),
            ChallengeChoice(id="blue", label="Azul"),
        ),
        correct_id="blue",
    )
    panel = ChallengePanel(
        root,
        spec,
        on_answer=lambda _spec, given: answers.append(given),
        feedback_ms=10,
        answer_delay_ms=200,
    )
    panel.pack()
    root.update()

    assert panel._locked is True
    assert panel._guidance.cget("text") == GUIDANCE_TEXT
    assert all(button.cget("state") == "disabled" for button in panel._buttons)

    panel._choose("blue")
    assert answers == []

    deadline = time.monotonic() + 2
    while panel._locked and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert panel._locked is False
    assert all(button.cget("state") == "normal" for button in panel._buttons)

    panel._choose("blue")
    deadline = time.monotonic() + 2
    while not answers and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert answers == ["blue"]
    root.destroy()


def test_challenge_panel_text_input_waits_before_submitting() -> None:
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
        prompt="Qual é o maior?\n\n7  ou  3",
        choices=(),
        correct_id="7",
        input_mode="text",
    )
    panel = ChallengePanel(
        root,
        spec,
        on_answer=lambda _spec, given: answers.append(given),
        feedback_ms=10,
        answer_delay_ms=200,
    )
    panel.pack()
    root.update()

    assert panel._entry is not None
    assert panel._entry.cget("state") == "disabled"
    panel._submit_text()
    assert answers == []
    assert panel._hint is not None
    assert panel._hint.cget("text") == ""

    deadline = time.monotonic() + 2
    while panel._locked and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert panel._entry.cget("state") == "normal"

    panel._entry.insert(0, "7")
    panel._submit_text()
    deadline = time.monotonic() + 2
    while not answers and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert answers == ["7"]
    root.destroy()


def test_overlay_wrong_answer_shows_wait_before_hiding(tmp_path, monkeypatch) -> None:
    from learning_helper.overlay import main_window

    monkeypatch.setattr(main_window, "DEBUG_WRONG_ANSWER_WAIT_SECONDS", 1)
    store = Store(tmp_path / "learning_helper.db")
    engine = AdaptiveEngine(store, rng=random.Random(0))
    try:
        try:
            app = OverlayApp(engine, RuntimeConfig(debug=True))
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        app._show_challenge()
        app.update()
        assert app._panel is not None

        spec = app._panel._spec
        wrong = next(
            choice.id for choice in spec.choices if not spec.is_correct(choice.id)
        )
        app._panel._feedback_ms = 10
        app._panel._locked = False
        app._panel._set_answers_enabled(True)
        app._panel._choose(wrong)

        deadline = time.monotonic() + 2
        while app._penalty_panel is None and time.monotonic() < deadline:
            app.update()
            time.sleep(0.01)
        assert app._penalty_panel is not None
        assert app._panel is None
        assert app._showing is True
        assert store.count_attempts() == 1
        assert store.recent_attempts(spec.module_id, 1)[0].is_correct is False

        deadline = time.monotonic() + 3
        while app._showing and time.monotonic() < deadline:
            app.update()
            time.sleep(0.01)
        assert app._showing is False
        assert app._penalty_panel is None
        app.destroy()
    finally:
        store.close()


def test_overlay_correct_answer_hides_without_wait(tmp_path) -> None:
    store = Store(tmp_path / "learning_helper.db")
    engine = AdaptiveEngine(store, rng=random.Random(0))
    try:
        try:
            app = OverlayApp(engine, RuntimeConfig(debug=True))
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        app._show_challenge()
        app.update()
        assert app._panel is not None

        spec = app._panel._spec
        app._panel._feedback_ms = 10
        app._panel._locked = False
        app._panel._set_answers_enabled(True)
        app._panel._choose(spec.correct_id)

        deadline = time.monotonic() + 2
        while app._showing and time.monotonic() < deadline:
            app.update()
            time.sleep(0.01)
        assert app._showing is False
        assert app._panel is None
        assert app._penalty_panel is None
        assert store.count_attempts() == 1
        assert store.recent_attempts(spec.module_id, 1)[0].is_correct is True
        app.destroy()
    finally:
        store.close()


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


def _start_exhausted_overlay(store, engine):
    from learning_helper.overlay.main_window import OverlayApp
    from learning_helper.usage import local_day_key

    store.add_daily_usage(local_day_key(), 10_000)
    try:
        app = OverlayApp(engine, RuntimeConfig(debug=True))
    except tkinter.TclError:
        pytest.skip("sem display disponível")
    deadline = time.monotonic() + 3
    while not app._daily_limit_visible and time.monotonic() < deadline:
        app.update()
        time.sleep(0.02)
    assert app._daily_limit_visible is True
    return app


def test_overlay_shows_daily_limit_when_usage_is_exhausted(tmp_path) -> None:
    store = Store(tmp_path / "learning_helper.db")
    engine = AdaptiveEngine(store, rng=random.Random(0))
    try:
        app = _start_exhausted_overlay(store, engine)
        assert app._daily_limit_panel is not None
        assert app._panel is None
        assert app._penalty_panel is None
        app._hide_daily_limit(resume=False)
        app.update()
        assert app._daily_limit_visible is False
        app.destroy()
    finally:
        store.close()


def test_daily_limit_extension_checks_password_and_minutes(tmp_path) -> None:
    from learning_helper.settings import Settings

    store = Store(tmp_path / "learning_helper.db")
    store.save_settings(Settings(extension_password_hash=hash_password("abcd")))
    engine = AdaptiveEngine(store, rng=random.Random(0))
    try:
        app = _start_exhausted_overlay(store, engine)

        assert app._on_extension_submit("errada", 5) == "Senha incorreta."
        assert app._on_extension_submit("abcd", 0) is not None
        assert app._daily_limit_visible is True
        assert app._daily_usage.extension_seconds == 0

        assert app._on_extension_submit("abcd", 5) is None
        assert app._daily_limit_visible is False
        assert app._daily_usage.extension_seconds == 5 * 60
        app.destroy()
    finally:
        store.close()


def test_daily_limit_without_password_keeps_extension_unavailable(tmp_path) -> None:
    store = Store(tmp_path / "learning_helper.db")
    engine = AdaptiveEngine(store, rng=random.Random(0))
    try:
        app = _start_exhausted_overlay(store, engine)

        app._on_daily_extend()
        app.update()

        assert app._extension_panel is None
        assert app._daily_limit_panel is not None
        assert "Nenhuma senha" in app._daily_limit_panel._error.cget("text")
        app.destroy()
    finally:
        store.close()


def test_daily_limit_adult_shortcut_pauses_and_hides(tmp_path) -> None:
    store = Store(tmp_path / "learning_helper.db")
    engine = AdaptiveEngine(store, rng=random.Random(0))
    try:
        app = _start_exhausted_overlay(store, engine)

        app._on_adult_pause()
        app.update()

        assert app._daily_limit_visible is False
        assert engine.is_paused() is True
        app.destroy()
    finally:
        store.close()


def test_settings_window_saves_daily_limit_and_password(tmp_path) -> None:
    from learning_helper.overlay.settings_window import SettingsWindow
    from learning_helper.security import verify_password

    store = Store(tmp_path / "learning_helper.db")
    try:
        try:
            window = SettingsWindow(store, first_run=False)
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        window._vars["daily_limit"].set("90")
        window._vars["extension_password"].set("abcd")
        window._vars["extension_password_confirm"].set("abcd")
        window._save()

        settings = store.get_settings()
        assert settings.daily_usage_limit_seconds == 90 * 60
        assert verify_password("abcd", settings.extension_password_hash) is True
    finally:
        store.close()


def test_settings_window_rejects_mismatched_password(tmp_path) -> None:
    from learning_helper.overlay.settings_window import SettingsWindow

    store = Store(tmp_path / "learning_helper.db")
    try:
        try:
            window = SettingsWindow(store, first_run=False)
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        window._vars["extension_password"].set("abcd")
        window._vars["extension_password_confirm"].set("abce")
        window._save()

        assert window.winfo_exists()
        assert "não confere" in window._status.cget("text")
        assert store.get_settings().extension_password_hash == ""
        window.destroy()
    finally:
        store.close()
