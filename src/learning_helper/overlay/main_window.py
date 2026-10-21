from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime, timezone

import customtkinter
from screeninfo import get_monitors

from learning_helper import lifecycle, reminders
from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.adaptive.models import ChallengeSpec
from learning_helper.challenges.registry import build_challenge
from learning_helper.config import (
    ADULT_SHORTCUT,
    BATHROOM_DEFER_SECONDS,
    DEBUG_BATHROOM_DURATION_SECONDS,
    DEBUG_BATHROOM_INTERVAL_SECONDS,
    RuntimeConfig,
)
from learning_helper.overlay.bathroom import BathroomPanel
from learning_helper.overlay.geometry import format_geometry
from learning_helper.overlay.host import ChallengePanel

PANEL_RELWIDTH = 0.62
PANEL_RELHEIGHT = 0.58

LOGGER = logging.getLogger(__name__)


def get_primary_monitor():
    try:
        monitors = get_monitors()
    except Exception:
        return None
    for monitor in monitors:
        if monitor.is_primary:
            return monitor
    return monitors[0] if monitors else None


class OverlayApp(customtkinter.CTk):
    """Janela única que cobre a tela e hospeda o desafio.

    O desafio é um painel dentro desta janela, e não outra toplevel: duas
    janelas disputando a camada "sempre no topo" se empilham de forma
    imprevisível (a override-redirect tende a ficar acima da gerenciada).
    """

    def __init__(
        self,
        engine: AdaptiveEngine,
        config: RuntimeConfig,
        *,
        update_service=None,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.config = config
        self._update_service = update_service
        self._panel: ChallengePanel | None = None
        self._showing = False
        self._job: str | None = None
        self._bathroom_panel: BathroomPanel | None = None
        self._bathroom_visible = False
        self._bathroom_job: str | None = None
        self._quit_job: str | None = None
        self._update_job: str | None = None

        customtkinter.set_appearance_mode("light")
        self.monitor = get_primary_monitor()

        self.withdraw()
        # Janela override-redirect: não é gerenciada pelo WM e, no X11, fica
        # empilhada acima das janelas normais. No Windows o empilhamento vem de
        # `-topmost`, aplicado em `_raise_above`.
        self.overrideredirect(True)
        self._raise_above()
        self.configure(fg_color="#000000")
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.bind_all(ADULT_SHORTCUT, lambda _event: self._on_adult_pause())
        self._apply_geometry()

        if self.config.debug:
            close_btn = tk.Button(self, text="close", command=self.quit)
            close_btn.place(x=10, y=10)

        self._schedule_bathroom()
        self._schedule_next()
        self._watch_quit()
        if self._update_service is not None:
            self._watch_updates()

    def _watch_quit(self) -> None:
        if lifecycle.quit_requested():
            self.quit()
            return
        self._quit_job = self.after(500, self._watch_quit)

    def _watch_updates(self) -> None:
        service = self._update_service
        pending = service.pending if service is not None else None
        if pending is None and service is not None:
            pending = service.accept_manual_request()
        if (
            pending is not None
            and not self._showing
            and not self._bathroom_visible
        ):
            try:
                if service.apply():
                    self.quit()
                    return
            except Exception:
                LOGGER.exception("Falha ao aplicar atualização")
        self._update_job = self.after(1000, self._watch_updates)

    def _apply_geometry(self) -> None:
        if self.monitor is None:
            self.geometry(
                format_geometry(self.winfo_screenwidth(), self.winfo_screenheight())
            )
            return
        self.geometry(
            format_geometry(
                self.monitor.width,
                self.monitor.height,
                self.monitor.x,
                self.monitor.y,
            )
        )

    def _raise_above(self) -> None:
        """Topmost no Windows; no X11 o override-redirect já empilha acima."""
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.lift()

    def _schedule_next(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
        settings = self.engine.settings()
        delay = self.config.delay_ms(
            self.engine.next_interval_seconds(),
            settings.min_interval_seconds,
            settings.max_interval_seconds,
        )
        pause_until = self.engine.profile().adult_pause_until
        if pause_until is not None:
            remaining_ms = int((pause_until - datetime.now(timezone.utc)).total_seconds() * 1000)
            if remaining_ms > delay:
                delay = remaining_ms
        self._job = self.after(max(delay, 200), self._show_challenge)

    def _show_challenge(self) -> None:
        if self._bathroom_visible:
            # O lembrete está na tela: espera ele terminar.
            self._job = self.after(BATHROOM_DEFER_SECONDS * 1000, self._show_challenge)
            return
        if self._showing:
            return
        if self.engine.is_paused():
            self._schedule_next()
            return
        self._showing = True
        module_id = self.engine.pick_module()
        level = self.engine.current_level(module_id)
        spec = build_challenge(module_id, level)
        self._panel = ChallengePanel(
            self,
            spec,
            on_answer=self._on_answer,
            feedback_ms=self.engine.settings().feedback_ms,
        )
        self._panel.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=PANEL_RELWIDTH,
            relheight=PANEL_RELHEIGHT,
        )
        self._apply_geometry()
        self.deiconify()
        self._raise_above()
        self.focus_force()
        self.after(50, self._raise_above)

    def _hide_overlay(self) -> None:
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None
        self._showing = False
        self.withdraw()

    def _schedule_bathroom(self, delay_seconds: int | None = None) -> None:
        if self._bathroom_job is not None:
            self.after_cancel(self._bathroom_job)
            self._bathroom_job = None
        profile = self.engine.profile()
        settings = self.engine.settings()
        if not settings.bathroom_reminder_enabled:
            return
        interval = (
            DEBUG_BATHROOM_INTERVAL_SECONDS
            if self.config.debug
            else settings.bathroom_interval_seconds
        )
        if delay_seconds is None:
            delay_seconds = reminders.seconds_until_next(
                profile.last_bathroom_reminder_at,
                datetime.now(timezone.utc),
                interval,
            )
        self._bathroom_job = self.after(
            max(int(delay_seconds * 1000), 200), self._show_bathroom
        )

    def _show_bathroom(self) -> None:
        self._bathroom_job = None
        if self._bathroom_visible:
            return
        settings = self.engine.settings()
        if not settings.bathroom_reminder_enabled:
            return
        if self.engine.is_paused() or self._showing:
            # Pausa do adulto ou desafio na tela: tenta de novo em seguida.
            self._schedule_bathroom(BATHROOM_DEFER_SECONDS)
            return
        duration = (
            DEBUG_BATHROOM_DURATION_SECONDS
            if self.config.debug
            else settings.bathroom_duration_seconds
        )
        self._bathroom_visible = True
        self.engine.record_bathroom_reminder()
        LOGGER.info("Lembrete de banheiro exibido por %s s", duration)
        self._bathroom_panel = BathroomPanel(
            self,
            seconds=duration,
            on_finished=self._hide_bathroom,
        )
        self._bathroom_panel.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=PANEL_RELWIDTH,
            relheight=PANEL_RELHEIGHT,
        )
        self._apply_geometry()
        self.deiconify()
        self._raise_above()
        self.focus_force()
        self.after(50, self._raise_above)

    def _hide_bathroom(self) -> None:
        if self._bathroom_panel is not None:
            self._bathroom_panel.cancel()
            self._bathroom_panel.destroy()
            self._bathroom_panel = None
        self._bathroom_visible = False
        if not self._showing:
            self.withdraw()
        self._schedule_bathroom()

    def _on_answer(self, spec: ChallengeSpec, given_answer: str) -> None:
        if not self._showing:
            return
        self.engine.record_attempt(spec, given_answer)
        self._hide_overlay()
        self._schedule_next()

    def _on_adult_pause(self) -> None:
        if self._bathroom_visible:
            self._hide_bathroom()
            self.engine.pause_for_adult()
            self._schedule_next()
            return
        if not self._showing:
            return
        self.engine.pause_for_adult()
        self._hide_overlay()
        self._schedule_next()
