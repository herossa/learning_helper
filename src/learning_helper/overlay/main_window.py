from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime, timezone

import customtkinter
from screeninfo import get_monitors

from learning_helper import lifecycle, power, reminders
from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.adaptive.models import ChallengeSpec
from learning_helper.challenges.registry import build_challenge
from learning_helper.config import (
    ADULT_SHORTCUT,
    BATHROOM_DEFER_SECONDS,
    DAILY_USAGE_TICK_MS,
    DEBUG_BATHROOM_DURATION_SECONDS,
    DEBUG_BATHROOM_INTERVAL_SECONDS,
    DEBUG_DAILY_USAGE_LIMIT_SECONDS,
    DEBUG_WRONG_ANSWER_WAIT_SECONDS,
    EXTENSION_MINUTES_MAX,
    EXTENSION_MINUTES_MIN,
    RuntimeConfig,
)
from learning_helper.overlay.bathroom import BathroomPanel
from learning_helper.overlay.countdown import WRONG_CARD_COLOR, CountdownPanel
from learning_helper.overlay.daily_limit import DailyLimitPanel, ExtensionPanel
from learning_helper.overlay.geometry import format_geometry
from learning_helper.overlay.host import ChallengePanel
from learning_helper.security import verify_password
from learning_helper.usage import DailyUsage

PANEL_RELWIDTH = 0.62
PANEL_RELHEIGHT = 0.58
SHOW_RETRY_MS = 1000

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
        self._penalty_panel: CountdownPanel | None = None
        self._showing = False
        self._job: str | None = None
        self._bathroom_panel: BathroomPanel | None = None
        self._bathroom_visible = False
        self._bathroom_job: str | None = None
        self._quit_job: str | None = None
        self._update_job: str | None = None
        self._daily_limit_panel: DailyLimitPanel | None = None
        self._extension_panel: ExtensionPanel | None = None
        self._daily_limit_visible = False
        self._daily_job: str | None = None
        settings = self.engine.settings()
        self._daily_usage = DailyUsage(
            self.engine.store,
            (
                DEBUG_DAILY_USAGE_LIMIT_SECONDS
                if self.config.debug
                else settings.daily_usage_limit_seconds
            ),
        )

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
            close_btn = tk.Button(self, text="close", command=self._quit_app)
            close_btn.place(x=10, y=10)

        self._schedule_bathroom()
        self._schedule_next()
        self._watch_quit()
        self._daily_job = self.after(200, self._watch_daily_usage)
        if self._update_service is not None:
            self._watch_updates()

    def _watch_quit(self) -> None:
        if lifecycle.quit_requested():
            self._quit_app()
            return
        self._quit_job = self.after(500, self._watch_quit)

    def _quit_app(self) -> None:
        self._flush_usage()
        self.quit()

    def _flush_usage(self) -> None:
        try:
            self._daily_usage.flush()
        except Exception:
            LOGGER.exception("Falha ao salvar o tempo diário de uso")

    def destroy(self) -> None:
        self._flush_usage()
        if self._daily_job is not None:
            try:
                self.after_cancel(self._daily_job)
            except tk.TclError:
                pass
            self._daily_job = None
        super().destroy()

    def _watch_updates(self) -> None:
        service = self._update_service
        pending = service.pending if service is not None else None
        if pending is None and service is not None:
            pending = service.accept_manual_request()
        if (
            pending is not None
            and not self._showing
            and not self._bathroom_visible
            and not self._daily_limit_visible
        ):
            try:
                if service.apply():
                    self._quit_app()
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
        if self._daily_limit_visible:
            self._job = self.after(SHOW_RETRY_MS, self._show_challenge)
            return
        if self._bathroom_visible:
            # O lembrete está na tela: espera ele terminar.
            self._job = self.after(BATHROOM_DEFER_SECONDS * 1000, self._show_challenge)
            return
        if self._showing:
            # Ainda há desafio ou espera na tela: tenta de novo em seguida.
            self._job = self.after(SHOW_RETRY_MS, self._show_challenge)
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
        if self._penalty_panel is not None:
            self._penalty_panel.cancel()
            self._penalty_panel.destroy()
            self._penalty_panel = None
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
        if self._daily_limit_visible or self._bathroom_visible:
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
        correct = spec.is_correct(given_answer)
        self.engine.record_attempt(spec, given_answer)
        # O intervalo começa na resposta; se ele vencer durante a espera, o
        # próximo desafio aguarda o fim do bloqueio.
        self._schedule_next()
        if correct:
            self._hide_overlay()
            return
        self._show_penalty()

    def _show_penalty(self, seconds: int | None = None) -> None:
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None
        if seconds is None:
            settings = self.engine.settings()
            seconds = (
                DEBUG_WRONG_ANSWER_WAIT_SECONDS
                if self.config.debug
                else settings.wrong_answer_wait_seconds
            )
        LOGGER.info("Espera após resposta errada exibida por %s s", seconds)
        self._penalty_panel = CountdownPanel(
            self,
            seconds=seconds,
            title="Quase! Aguarde um pouco.",
            subtitle="Leia a pergunta com calma. Você poderá responder quando o tempo acabar.",
            fg_color=WRONG_CARD_COLOR,
            on_finished=self._hide_overlay,
        )
        self._penalty_panel.place(
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

    def _watch_daily_usage(self) -> None:
        try:
            day_changed = self._daily_usage.tick(
                active=not self._daily_limit_visible
            )
            if self._daily_limit_visible:
                if day_changed or not self._daily_usage.is_exhausted:
                    self._hide_daily_limit(resume=True)
            elif (
                self._daily_usage.is_exhausted
                and not self.engine.is_paused()
            ):
                self._show_daily_limit()
        except Exception:
            LOGGER.exception("Falha ao atualizar o tempo diário de uso")
        try:
            self._daily_job = self.after(
                DAILY_USAGE_TICK_MS, self._watch_daily_usage
            )
        except tk.TclError:
            pass

    def _show_daily_limit(self) -> None:
        if self._daily_limit_visible:
            return
        self._daily_usage.flush()
        self._clear_transient_panels()
        self._daily_limit_visible = True
        LOGGER.info(
            "Limite diário atingido: %s de %s segundos",
            self._daily_usage.used_seconds,
            self._daily_usage.total_allowed_seconds,
        )
        self._render_daily_limit()

    def _render_daily_limit(self) -> None:
        if self._extension_panel is not None:
            self._extension_panel.destroy()
            self._extension_panel = None
        if self._daily_limit_panel is not None:
            self._daily_limit_panel.destroy()
        self._daily_limit_panel = DailyLimitPanel(
            self,
            base_limit_seconds=self._daily_usage.daily_limit_seconds,
            used_seconds=self._daily_usage.used_seconds,
            extension_seconds=self._daily_usage.extension_seconds,
            on_shutdown=self._on_daily_shutdown,
            on_extend=self._on_daily_extend,
        )
        self._place_blocking_panel(self._daily_limit_panel)

    def _hide_daily_limit(self, *, resume: bool) -> None:
        if self._daily_limit_panel is not None:
            self._daily_limit_panel.destroy()
            self._daily_limit_panel = None
        if self._extension_panel is not None:
            self._extension_panel.destroy()
            self._extension_panel = None
        self._daily_limit_visible = False
        self.withdraw()
        if resume and not self.engine.is_paused():
            self._schedule_next()
            self._schedule_bathroom()

    def _clear_transient_panels(self) -> None:
        for attribute in ("_job", "_bathroom_job"):
            job = getattr(self, attribute)
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, attribute, None)
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None
        if self._penalty_panel is not None:
            self._penalty_panel.cancel()
            self._penalty_panel.destroy()
            self._penalty_panel = None
        if self._bathroom_panel is not None:
            self._bathroom_panel.cancel()
            self._bathroom_panel.destroy()
            self._bathroom_panel = None
        self._showing = False
        self._bathroom_visible = False

    def _place_blocking_panel(self, panel) -> None:
        panel.place(
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

    def _on_daily_extend(self) -> None:
        if not self.engine.settings().extension_password_hash:
            if self._daily_limit_panel is not None:
                self._daily_limit_panel.show_error(
                    "Nenhuma senha de extensão configurada. "
                    "Peça a um adulto para configurar em Configurações."
                )
            return
        if self._daily_limit_panel is not None:
            self._daily_limit_panel.destroy()
            self._daily_limit_panel = None
        self._extension_panel = ExtensionPanel(
            self,
            on_submit=self._on_extension_submit,
            on_cancel=self._on_extension_cancel,
        )
        self._place_blocking_panel(self._extension_panel)

    def _on_extension_cancel(self) -> None:
        if self._extension_panel is not None:
            self._extension_panel.destroy()
            self._extension_panel = None
        self._render_daily_limit()

    def _on_extension_submit(
        self, password: str, minutes: int
    ) -> str | None:
        settings = self.engine.settings()
        if not settings.extension_password_hash:
            return "Nenhuma senha de extensão configurada."
        if not verify_password(password, settings.extension_password_hash):
            return "Senha incorreta."
        if not EXTENSION_MINUTES_MIN <= minutes <= EXTENSION_MINUTES_MAX:
            return (
                f"Os minutos devem ficar entre {EXTENSION_MINUTES_MIN} e "
                f"{EXTENSION_MINUTES_MAX}."
            )
        self._daily_usage.extend(minutes)
        LOGGER.info(
            "Tempo diário estendido em %s minutos (usado %s s, "
            "limite efetivo %s s, restante %s s)",
            minutes,
            self._daily_usage.used_seconds,
            self._daily_usage.total_allowed_seconds,
            self._daily_usage.remaining_seconds,
        )
        self._hide_daily_limit(resume=True)
        return None

    def _on_daily_shutdown(self) -> None:
        try:
            power.request_shutdown()
        except power.ShutdownError as exc:
            LOGGER.warning("Falha ao desligar o computador: %s", exc)
            if self._daily_limit_panel is not None:
                self._daily_limit_panel.show_error(str(exc))
            return
        LOGGER.info("Desligamento do computador solicitado")
        self._quit_app()

    def _on_adult_pause(self) -> None:
        if self._daily_limit_visible:
            self._hide_daily_limit(resume=False)
            self.engine.pause_for_adult()
            self._schedule_next()
            self._schedule_bathroom()
            return
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
