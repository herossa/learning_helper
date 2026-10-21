from __future__ import annotations

import tkinter as tk
from datetime import datetime, timezone

import customtkinter
from screeninfo import get_monitors

from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.challenges.registry import build_challenge
from learning_helper.config import ADULT_SHORTCUT, RuntimeConfig
from learning_helper.overlay.host import ChallengeHost


def get_primary_monitor():
    monitors = get_monitors()
    for monitor in monitors:
        if monitor.is_primary:
            return monitor
    return monitors[0] if monitors else None


class OverlayApp(customtkinter.CTk):
    def __init__(self, engine: AdaptiveEngine, config: RuntimeConfig) -> None:
        super().__init__()
        self.engine = engine
        self.config = config
        self._host: ChallengeHost | None = None
        self._showing = False
        self._job: str | None = None

        self.withdraw()
        self.monitor = get_primary_monitor()
        self.bind_all(ADULT_SHORTCUT, lambda _event: self._on_adult_pause())

        self._dimmer = customtkinter.CTkToplevel(self)
        self._dimmer.withdraw()
        self._dimmer.overrideredirect(True)
        self._dimmer.attributes("-topmost", True)
        self._dimmer.protocol("WM_DELETE_WINDOW", lambda: None)
        if self.monitor is not None:
            self._dimmer.geometry(
                f"{self.monitor.width}x{self.monitor.height}+{self.monitor.x}+{self.monitor.y}"
            )
        self._dimmer.configure(fg_color="black")
        try:
            self._dimmer.attributes("-alpha", 0.5)
        except tk.TclError:
            pass

        if self.config.debug:
            close_btn = tk.Button(self._dimmer, text="close", command=self.quit)
            close_btn.place(x=10, y=10)

        self.after(200, self._show_challenge)

    def _schedule_next(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
        delay = self.config.interval_ms
        pause_until = self.engine.profile().adult_pause_until
        if pause_until is not None:
            remaining_ms = int((pause_until - datetime.now(timezone.utc)).total_seconds() * 1000)
            if remaining_ms > delay:
                delay = remaining_ms
        self._job = self.after(max(delay, 200), self._show_challenge)

    def _challenge_geometry(self) -> tuple[int, int, int, int]:
        if self.monitor is None:
            return 800, 500, 100, 100
        width = int(self.monitor.width * 0.58)
        height = int(self.monitor.height * 0.65)
        x = self.monitor.x + (self.monitor.width - width) // 2
        y = self.monitor.y + (self.monitor.height - height) // 2
        return width, height, x, y

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
        self._dimmer.deiconify()
        self._dimmer.lift()
        self._host = ChallengeHost(
            self._dimmer,
            spec,
            on_answer=self._on_answer,
            on_adult_pause=self._on_adult_pause,
            geometry=self._challenge_geometry(),
        )

    def _hide_overlay(self) -> None:
        if self._host is not None:
            try:
                self._host.destroy()
            except tk.TclError:
                pass
            self._host = None
        self._dimmer.withdraw()
        self._showing = False

    def _on_answer(self, given_answer: str) -> None:
        if self._host is None:
            return
        spec = self._host._spec
        self.engine.record_attempt(spec, given_answer)
        self._host = None
        self._dimmer.withdraw()
        self._showing = False
        self._schedule_next()

    def _on_adult_pause(self) -> None:
        if not self._showing:
            return
        self.engine.pause_for_adult(self.config.adult_pause_seconds)
        self._hide_overlay()
        self._schedule_next()
