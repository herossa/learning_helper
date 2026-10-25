"""Tela de configuração (primeira execução e ferramenta avulsa)."""

from __future__ import annotations

import math
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox

import customtkinter

from learning_helper import __version__, autostart, lifecycle
from learning_helper.config import MODULE_LABELS, MODULE_ORDER
from learning_helper.persistence.db import Store, data_dir
from learning_helper.settings import Settings

CARD_COLOR = "#f7f7f7"
TEXT_MUTED = "#555555"


def _fmt_minutes(seconds: int) -> str:
    return f"{seconds / 60:g}"


def _fmt_percent(ratio: float) -> str:
    return f"{ratio * 100:g}"


def _fmt_seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:g}"


class SettingsWindow(customtkinter.CTk):
    def __init__(self, store: Store, *, first_run: bool = False) -> None:
        super().__init__()
        self._store = store
        self._first_run = first_run
        self._vars: dict[str, tk.StringVar] = {}
        self._module_vars: dict[str, tk.BooleanVar] = {}
        self._autostart_var: tk.BooleanVar | None = None
        self._update_var: tk.BooleanVar | None = None
        self._update_status: customtkinter.CTkLabel | None = None
        self._update_button: customtkinter.CTkButton | None = None
        self._updating = False
        self._ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._needs_initial_interval = (
            not store.onboarding_completed() and store.count_attempts() == 0
        )

        customtkinter.set_appearance_mode("light")
        self.title(
            "Primeira configuração — Learning Helper"
            if first_run
            else "Configurações — Learning Helper"
        )
        self.geometry("820x780")
        self.minsize(720, 640)
        self.configure(fg_color="#ffffff")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()
        self._apply_settings(store.get_settings())
        self.after(60, self.focus_force)
        self.after(100, self._poll_ui_queue)
        self.after(500, self._watch_quit)

    def _build(self) -> None:
        header = customtkinter.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(22, 0))
        customtkinter.CTkLabel(
            header,
            text="Bem-vindo!" if self._first_run else "Configurações",
            font=("Arial", 26, "bold"),
            anchor="w",
        ).pack(anchor="w")
        subtitle = (
            "Ajuste o Learning Helper antes do primeiro desafio. "
            "Fechar esta janela usa os padrões."
            if self._first_run
            else "As mudanças valem a partir do próximo início do Learning Helper."
        )
        customtkinter.CTkLabel(
            header,
            text=subtitle,
            font=("Arial", 13),
            text_color=TEXT_MUTED,
            justify="left",
            wraplength=740,
        ).pack(anchor="w", pady=(4, 0))

        body = customtkinter.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        body.pack(fill="both", expand=True, padx=18, pady=(10, 0))

        self._build_learning(body)
        self._build_accuracy(body)
        self._build_routine(body)
        self._build_modules(body)
        self._build_data(body)
        if not self._first_run:
            self._build_updates(body)

        footer = customtkinter.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=28, pady=(8, 18))
        self._status = customtkinter.CTkLabel(
            footer, text="", text_color="#b00020", justify="left", wraplength=740
        )
        self._status.pack(anchor="w", pady=(0, 6))

        buttons = customtkinter.CTkFrame(footer, fg_color="transparent")
        buttons.pack(anchor="e")
        customtkinter.CTkButton(
            buttons,
            text="Restaurar padrões",
            fg_color="transparent",
            border_width=1,
            text_color="#333333",
            command=self._reset_defaults,
            width=150,
        ).pack(side="left", padx=(0, 8))
        customtkinter.CTkButton(
            buttons,
            text="Usar padrões" if self._first_run else "Cancelar",
            fg_color="transparent",
            border_width=1,
            text_color="#333333",
            command=self._on_close,
            width=120,
        ).pack(side="left", padx=(0, 8))
        customtkinter.CTkButton(
            buttons,
            text="Salvar e começar" if self._first_run else "Salvar",
            command=self._save,
            width=150,
        ).pack(side="left")

    def _section(self, parent, title: str) -> customtkinter.CTkFrame:
        card = customtkinter.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=16)
        card.pack(fill="x", padx=10, pady=8)
        customtkinter.CTkLabel(
            card, text=title, font=("Arial", 18, "bold"), anchor="w"
        ).pack(anchor="w", padx=18, pady=(14, 4))
        return card

    def _entry_row(
        self,
        parent,
        key: str,
        label: str,
        suffix: str = "",
        width: int = 100,
    ) -> None:
        row = customtkinter.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=4)
        customtkinter.CTkLabel(
            row, text=label, anchor="w", width=360, justify="left"
        ).pack(side="left")
        variable = tk.StringVar()
        self._vars[key] = variable
        customtkinter.CTkEntry(
            row, textvariable=variable, width=width, justify="right"
        ).pack(side="left", padx=(8, 6))
        if suffix:
            customtkinter.CTkLabel(row, text=suffix, anchor="w").pack(side="left")

    def _caption(self, parent, text: str) -> None:
        customtkinter.CTkLabel(
            parent,
            text=text,
            font=("Arial", 12),
            text_color=TEXT_MUTED,
            justify="left",
            anchor="w",
            wraplength=700,
        ).pack(anchor="w", padx=18, pady=(0, 10))

    def _build_learning(self, parent) -> None:
        card = self._section(parent, "Ritmo dos desafios")
        self._entry_row(card, "initial", "Intervalo inicial entre desafios", "min")
        self._entry_row(card, "minimum", "Intervalo mínimo", "min")
        self._entry_row(card, "maximum", "Intervalo máximo", "min")
        self._entry_row(card, "step", "Quanto acerto/erro muda o intervalo", "s")
        self._caption(
            card,
            "O intervalo inicial vale para perfis novos. O intervalo atual da "
            "criança continua sendo ajustado automaticamente dentro do mínimo e "
            "do máximo.",
        )

    def _build_accuracy(self, parent) -> None:
        card = self._section(parent, "Precisão e níveis")
        self._entry_row(card, "window", "Tentativas por bloco de avaliação", "tentativas")
        self._entry_row(card, "unlock", "Acerto para desbloquear o próximo módulo", "%")
        self._entry_row(card, "up", "Acerto para subir de nível", "%")
        self._entry_row(card, "down", "Acerto máximo para descer de nível", "%")
        self._entry_row(card, "max_level", "Nível máximo", "níveis")
        self._entry_row(card, "feedback", "Duração do feedback de acerto/erro", "s")
        self._caption(
            card,
            "Os limiares são avaliados a cada bloco de tentativas do módulo.",
        )

    def _build_routine(self, parent) -> None:
        card = self._section(parent, "Rotina")
        self._entry_row(card, "adult_pause", "Pausa do adulto", "min")
        self._entry_row(
            card,
            "wrong_answer_wait",
            "Espera após resposta errada",
            "s",
        )
        self._entry_row(card, "bathroom_interval", "Intervalo do lembrete de banheiro", "min")
        self._entry_row(card, "bathroom_duration", "Duração do lembrete de banheiro", "s")

        bathroom_row = customtkinter.CTkFrame(card, fg_color="transparent")
        bathroom_row.pack(fill="x", padx=18, pady=4)
        customtkinter.CTkLabel(
            bathroom_row, text="Lembrete de banheiro ativo", anchor="w", width=360
        ).pack(side="left")
        self._bathroom_switch = customtkinter.CTkSwitch(
            bathroom_row, text="", onvalue=True, offvalue=False
        )
        self._bathroom_switch.pack(side="left", padx=(8, 0))

        if autostart.SUPPORTED:
            autostart_row = customtkinter.CTkFrame(card, fg_color="transparent")
            autostart_row.pack(fill="x", padx=18, pady=(4, 12))
            customtkinter.CTkLabel(
                autostart_row,
                text="Iniciar junto com o usuário (autostart)",
                anchor="w",
                width=360,
            ).pack(side="left")
            self._autostart_var = tk.BooleanVar(value=autostart.is_enabled())
            customtkinter.CTkSwitch(
                autostart_row,
                text="",
                variable=self._autostart_var,
                onvalue=True,
                offvalue=False,
            ).pack(side="left", padx=(8, 0))
        else:
            self._caption(
                card,
                "No Windows, o início automático é gerenciado pelo instalador.",
            )

    def _build_modules(self, parent) -> None:
        card = self._section(parent, "Módulos ativos")
        grid = customtkinter.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=18, pady=(0, 6))
        for index, module in enumerate(MODULE_ORDER):
            variable = tk.BooleanVar(value=True)
            self._module_vars[module] = variable
            customtkinter.CTkCheckBox(
                grid,
                text=MODULE_LABELS[module],
                variable=variable,
                onvalue=True,
                offvalue=False,
            ).grid(row=index // 2, column=index % 2, sticky="w", padx=8, pady=4)
        self._caption(
            card,
            "Desativar não apaga o progresso: o módulo volta ao reativar. O "
            "desbloqueio pula os módulos desativados.",
        )

    def _build_data(self, parent) -> None:
        card = self._section(parent, "Dados")
        customtkinter.CTkLabel(
            card,
            text=f"Banco: {self._store.db_path}",
            font=("Arial", 12),
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 6))
        customtkinter.CTkButton(
            card,
            text="Abrir pasta de dados",
            fg_color="transparent",
            border_width=1,
            text_color="#333333",
            command=self._open_folder,
            width=160,
        ).pack(anchor="w", padx=18, pady=(0, 14))

    def _build_updates(self, parent) -> None:
        card = self._section(parent, "Atualizações")
        customtkinter.CTkLabel(
            card,
            text=f"Versão atual: {__version__}",
            font=("Arial", 12),
            text_color=TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w", padx=18, pady=(0, 6))

        row = customtkinter.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=4)
        customtkinter.CTkLabel(
            row, text="Verificar atualizações ao iniciar", anchor="w", width=360
        ).pack(side="left")
        self._update_var = tk.BooleanVar(value=True)
        customtkinter.CTkSwitch(
            row,
            text="",
            variable=self._update_var,
            onvalue=True,
            offvalue=False,
        ).pack(side="left", padx=(8, 0))

        self._update_button = customtkinter.CTkButton(
            card,
            text="Verificar atualizações agora",
            fg_color="transparent",
            border_width=1,
            text_color="#333333",
            command=self._check_updates_async,
            width=220,
        )
        self._update_button.pack(anchor="w", padx=18, pady=(8, 4))
        self._update_status = customtkinter.CTkLabel(
            card,
            text="",
            font=("Arial", 12),
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=700,
            justify="left",
        )
        self._update_status.pack(anchor="w", padx=18, pady=(0, 4))
        self._caption(
            card,
            "Em builds instalados, a nova versão é baixada em segundo plano e "
            "instalada silenciosamente, sem interromper um desafio na tela.",
        )

    def _watch_quit(self) -> None:
        if lifecycle.quit_requested():
            self.destroy()
            return
        try:
            self.after(500, self._watch_quit)
        except tk.TclError:
            pass

    def _post(self, callback: Callable[[], None]) -> None:
        self._ui_queue.put(callback)

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                callback = self._ui_queue.get_nowait()
                try:
                    callback()
                except tk.TclError:
                    pass
        except queue.Empty:
            pass
        try:
            self.after(100, self._poll_ui_queue)
        except tk.TclError:
            pass

    def _set_update_status(self, text: str) -> None:
        if self._update_status is None:
            return
        try:
            self._update_status.configure(text=text)
        except tk.TclError:
            pass

    def _reset_update_button(self) -> None:
        if self._update_button is None:
            return
        try:
            self._update_button.configure(state="normal")
        except tk.TclError:
            pass

    def _finish_update(self) -> None:
        self._updating = False
        self._reset_update_button()

    def _check_updates_async(self) -> None:
        if self._updating:
            return
        self._updating = True
        if self._update_button is not None:
            self._update_button.configure(state="disabled")
        self._set_update_status("Verificando atualizações...")
        threading.Thread(
            target=self._check_updates_worker,
            name="learning-helper-manual-update",
            daemon=True,
        ).start()

    def _check_updates_worker(self) -> None:
        try:
            from learning_helper.single_instance import SingleInstance
            from learning_helper.updates.client import fetch_manifest
            from learning_helper.updates.install import apply_pending, asset_key
            from learning_helper.updates.manifest import is_newer
            from learning_helper.updates.service import (
                clear_manual_request,
                prepare_update,
                request_manual_update,
            )
            from learning_helper.updates.state import (
                load_state,
                record_attempt,
                save_state,
            )

            release = fetch_manifest()
            if not is_newer(release.version, __version__):
                self._post(
                    lambda: self._set_update_status(
                        f"Você está na versão mais recente ({__version__})."
                    )
                )
                return
            if asset_key() is None:
                self._post(
                    lambda: self._set_update_status(
                        f"Nova versão {release.version} disponível; "
                        "instalação automática indisponível nesta execução."
                    )
                )
                return

            version = release.version
            self._post(
                lambda: self._set_update_status(f"Baixando {version}...")
            )
            pending = prepare_update(
                release, __version__, data_dir(), force=True
            )
            if pending is None:
                self._post(
                    lambda: self._set_update_status(
                        "Não há pacote de atualização para esta instalação."
                    )
                )
                return
            base = data_dir()
            lock = SingleInstance(base / "app.lock")
            if not lock.acquire():
                # O app principal está aberto: o overlay aplica quando a tela
                # estiver livre. Assim não há dois instaladores ao mesmo tempo.
                request_manual_update(base, version)
                self._post(
                    lambda: self._set_update_status(
                        f"Atualização {version} baixada; ela será instalada "
                        "quando a tela estiver livre."
                    )
                )
                return
            try:
                state = load_state(base)
                record_attempt(state, pending.version, pending.path)
                save_state(base, state)
                clear_manual_request(base)
                self._post(
                    lambda: self._set_update_status(f"Instalando {version}...")
                )
                apply_pending(pending, base)
                self._post(self.destroy)
            finally:
                lock.release()
        except Exception as exc:
            message = str(exc)
            self._post(
                lambda: self._set_update_status(
                    f"Não foi possível atualizar: {message}"
                )
            )
        finally:
            self._post(self._finish_update)

    def _apply_settings(self, settings: Settings) -> None:
        values = {
            "initial": _fmt_minutes(settings.initial_interval_seconds),
            "minimum": _fmt_minutes(settings.min_interval_seconds),
            "maximum": _fmt_minutes(settings.max_interval_seconds),
            "step": str(settings.interval_step_seconds),
            "window": str(settings.accuracy_window),
            "unlock": _fmt_percent(settings.unlock_threshold),
            "up": _fmt_percent(settings.level_up_threshold),
            "down": _fmt_percent(settings.level_down_threshold),
            "max_level": str(settings.max_level),
            "feedback": _fmt_seconds(settings.feedback_ms),
            "adult_pause": _fmt_minutes(settings.adult_pause_seconds),
            "wrong_answer_wait": str(settings.wrong_answer_wait_seconds),
            "bathroom_interval": _fmt_minutes(settings.bathroom_interval_seconds),
            "bathroom_duration": str(settings.bathroom_duration_seconds),
        }
        for key, value in values.items():
            self._vars[key].set(value)
        if settings.bathroom_reminder_enabled:
            self._bathroom_switch.select()
        else:
            self._bathroom_switch.deselect()
        for module, variable in self._module_vars.items():
            variable.set(module in settings.enabled_modules)
        if self._autostart_var is not None:
            self._autostart_var.set(autostart.is_enabled())
        if self._update_var is not None:
            self._update_var.set(settings.update_check_on_startup)

    def _reset_defaults(self) -> None:
        self._apply_settings(Settings())
        self._status.configure(text="")

    def _show_errors(self, errors: list[str]) -> None:
        visible = errors[:3]
        text = "\n".join(f"• {error}" for error in visible)
        if len(errors) > len(visible):
            text += "\n• …"
        self._status.configure(text=text)

    def _number(
        self,
        key: str,
        label: str,
        errors: list[str],
    ) -> float | None:
        raw = self._vars[key].get().strip().replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            errors.append(f"{label}: informe um número.")
            return None
        if not math.isfinite(value):
            errors.append(f"{label}: informe um número finito.")
            return None
        return value

    def _collect(self) -> Settings | None:
        errors: list[str] = []
        initial = self._number("initial", "Intervalo inicial", errors)
        minimum = self._number("minimum", "Intervalo mínimo", errors)
        maximum = self._number("maximum", "Intervalo máximo", errors)
        step = self._number("step", "Passo do intervalo", errors)
        window = self._number("window", "Janela de precisão", errors)
        unlock = self._number("unlock", "Desbloqueio", errors)
        up = self._number("up", "Subir de nível", errors)
        down = self._number("down", "Descer de nível", errors)
        max_level = self._number("max_level", "Nível máximo", errors)
        feedback = self._number("feedback", "Feedback", errors)
        adult_pause = self._number("adult_pause", "Pausa do adulto", errors)
        wrong_answer_wait = self._number(
            "wrong_answer_wait", "Espera após resposta errada", errors
        )
        bathroom_interval = self._number(
            "bathroom_interval", "Intervalo do banheiro", errors
        )
        bathroom_duration = self._number(
            "bathroom_duration", "Duração do banheiro", errors
        )
        if errors:
            self._show_errors(errors)
            return None

        settings = Settings(
            initial_interval_seconds=int(round(initial * 60)),
            min_interval_seconds=int(round(minimum * 60)),
            max_interval_seconds=int(round(maximum * 60)),
            interval_step_seconds=int(round(step)),
            accuracy_window=int(round(window)),
            unlock_threshold=unlock / 100,
            level_up_threshold=up / 100,
            level_down_threshold=down / 100,
            max_level=int(round(max_level)),
            feedback_ms=int(round(feedback * 1000)),
            wrong_answer_wait_seconds=int(round(wrong_answer_wait)),
            adult_pause_seconds=int(round(adult_pause * 60)),
            bathroom_reminder_enabled=bool(self._bathroom_switch.get()),
            bathroom_interval_seconds=int(round(bathroom_interval * 60)),
            bathroom_duration_seconds=int(round(bathroom_duration)),
            enabled_modules=tuple(
                module
                for module in MODULE_ORDER
                if self._module_vars[module].get()
            ),
            update_check_on_startup=(
                bool(self._update_var.get())
                if self._update_var is not None
                else True
            ),
        )
        problems = settings.validate()
        if problems:
            self._show_errors(problems)
            return None
        return settings

    def _autostart_warning(self) -> str | None:
        if self._autostart_var is None:
            return None
        desired = bool(self._autostart_var.get())
        try:
            if desired and not autostart.is_enabled():
                autostart.enable_autostart()
            elif not desired and autostart.is_enabled():
                autostart.disable_autostart()
        except OSError as exc:
            return f"Não foi possível alterar o autostart: {exc}"
        return None

    def _persist(self, settings: Settings) -> bool:
        try:
            self._store.save_settings(settings)
        except Exception as exc:
            self._show_errors([f"Não foi possível salvar: {exc}"])
            return False
        if self._needs_initial_interval:
            profile = self._store.get_profile()
            profile.interval_seconds = settings.initial_interval_seconds
            self._store.save_profile(profile)
            self._needs_initial_interval = False
        self._store.complete_onboarding()
        return True

    def _save(self) -> None:
        settings = self._collect()
        if settings is None:
            return
        if not self._persist(settings):
            return
        warning = self._autostart_warning()
        if warning:
            messagebox.showwarning("Configurações", warning)
        self.destroy()

    def _on_close(self) -> None:
        if not self._first_run:
            self.destroy()
            return
        # Fechar na primeira execução equivale a "usar padrões".
        if not self._persist(Settings()):
            return
        self._autostart_warning()
        self.destroy()

    def _open_folder(self) -> None:
        folder = self._store.db_path.parent
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(
                    ["xdg-open", str(folder)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except OSError as exc:
            self._show_errors([f"Não foi possível abrir a pasta: {exc}"])


def run_settings_window(store: Store, *, first_run: bool = False) -> int:
    window = SettingsWindow(store, first_run=first_run)
    window.mainloop()
    return 0
