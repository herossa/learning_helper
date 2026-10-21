from __future__ import annotations

import tkinter as tk
from datetime import datetime, timezone

import customtkinter
from screeninfo import get_monitors

from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.adaptive.models import ChallengeSpec
from learning_helper.challenges.registry import build_challenge
from learning_helper.config import ADULT_SHORTCUT, RuntimeConfig
from learning_helper.overlay.host import ChallengePanel

PANEL_RELWIDTH = 0.62
PANEL_RELHEIGHT = 0.58


def get_primary_monitor():
    monitors = get_monitors()
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

    def __init__(self, engine: AdaptiveEngine, config: RuntimeConfig) -> None:
        super().__init__()
        self.engine = engine
        self.config = config
        self._panel: ChallengePanel | None = None
        self._showing = False
        self._job: str | None = None

        customtkinter.set_appearance_mode("light")
        self.monitor = get_primary_monitor()

        self.withdraw()
        # Janela override-redirect: não é gerenciada pelo WM e, por isso, fica
        # empilhada acima das janelas normais. `-topmost` é ignorado nesse modo.
        self.overrideredirect(True)
        self.configure(fg_color="#000000")
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.bind_all(ADULT_SHORTCUT, lambda _event: self._on_adult_pause())
        self._apply_geometry()

        if self.config.debug:
            close_btn = tk.Button(self, text="close", command=self.quit)
            close_btn.place(x=10, y=10)

        self.after(200, self._show_challenge)

    def _apply_geometry(self) -> None:
        if self.monitor is None:
            return
        self.geometry(
            f"{self.monitor.width}x{self.monitor.height}+{self.monitor.x}+{self.monitor.y}"
        )

    def _schedule_next(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
        delay = self.config.delay_ms(self.engine.next_interval_seconds())
        pause_until = self.engine.profile().adult_pause_until
        if pause_until is not None:
            remaining_ms = int((pause_until - datetime.now(timezone.utc)).total_seconds() * 1000)
            if remaining_ms > delay:
                delay = remaining_ms
        self._job = self.after(max(delay, 200), self._show_challenge)

    def _show_challenge(self) -> None:
        if self._showing:
            return
        if self.engine.is_paused():
            self._schedule_next()
            return
        self._showing = True
        module_id = self.engine.pick_module()
        level = self.engine.current_level(module_id)
        spec = build_challenge(module_id, level)
        self._panel = ChallengePanel(self, spec, on_answer=self._on_answer)
        self._panel.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=PANEL_RELWIDTH,
            relheight=PANEL_RELHEIGHT,
        )
        self._apply_geometry()
        self.deiconify()
        self.lift()
        self.focus_force()
        self.after(50, self.lift)

    def _hide_overlay(self) -> None:
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None
        self._showing = False
        self.withdraw()

    def _on_answer(self, spec: ChallengeSpec, given_answer: str) -> None:
        if not self._showing:
            return
        self.engine.record_attempt(spec, given_answer)
        self._hide_overlay()
        self._schedule_next()

    def _on_adult_pause(self) -> None:
        if not self._showing:
            return
        self.engine.pause_for_adult(self.config.adult_pause_seconds)
        self._hide_overlay()
        self._schedule_next()
