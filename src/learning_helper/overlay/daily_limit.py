from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter

from learning_helper.config import EXTENSION_MINUTES_MAX, EXTENSION_MINUTES_MIN
from learning_helper.usage import format_duration

CARD_COLOR = "#fff3df"
TEXT_MUTED = "#555555"
ERROR_COLOR = "#b00020"


class DailyLimitPanel(customtkinter.CTkFrame):
    """Bloqueio de tela quando o tempo diário de uso termina."""

    def __init__(
        self,
        parent,
        *,
        base_limit_seconds: int,
        used_seconds: int,
        extension_seconds: int,
        on_shutdown: Callable[[], None],
        on_extend: Callable[[], None],
    ) -> None:
        super().__init__(parent, corner_radius=24, fg_color=CARD_COLOR)
        self._on_shutdown = on_shutdown

        customtkinter.CTkLabel(
            self,
            text="O tempo de uso diário terminou.",
            font=("Arial", 34, "bold"),
            justify="center",
            wraplength=700,
        ).pack(pady=(54, 12))
        summary = [
            f"Limite diário: {format_duration(base_limit_seconds)}.",
            f"Tempo usado hoje: {format_duration(used_seconds)}.",
        ]
        if extension_seconds > 0:
            summary.append(
                "Tempo extra desta sessão: "
                f"{format_duration(extension_seconds)}."
            )
        customtkinter.CTkLabel(
            self,
            text="\n".join(summary),
            font=("Arial", 22),
            text_color=TEXT_MUTED,
            justify="center",
            wraplength=700,
        ).pack(pady=(0, 10))
        customtkinter.CTkLabel(
            self,
            text=(
                "Peça a um adulto para estender o tempo ou desligue o "
                "computador para continuar amanhã."
            ),
            font=("Arial", 18),
            text_color=TEXT_MUTED,
            justify="center",
            wraplength=700,
        ).pack(pady=(0, 28))

        buttons = customtkinter.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=(0, 18))
        self._shutdown_button = customtkinter.CTkButton(
            buttons,
            text="Desligar computador",
            width=230,
            height=64,
            font=("Arial", 20),
            fg_color="transparent",
            border_width=1,
            text_color="#333333",
            command=self._shutdown,
        )
        self._shutdown_button.pack(side="left", padx=(0, 14))
        customtkinter.CTkButton(
            buttons,
            text="Estender tempo",
            width=230,
            height=64,
            font=("Arial", 20),
            command=on_extend,
        ).pack(side="left")

        self._error = customtkinter.CTkLabel(
            self,
            text="",
            font=("Arial", 16),
            text_color=ERROR_COLOR,
            justify="center",
            wraplength=700,
        )
        self._error.pack(pady=(0, 36))

    def _shutdown(self) -> None:
        self._shutdown_button.configure(state="disabled")
        self._on_shutdown()

    def show_error(self, message: str) -> None:
        self._error.configure(text=message)
        self._shutdown_button.configure(state="normal")


class ExtensionPanel(customtkinter.CTkFrame):
    """Formulário de senha + minutos para liberar mais tempo."""

    def __init__(
        self,
        parent,
        *,
        on_submit: Callable[[str, int], str | None],
        on_cancel: Callable[[], None],
    ) -> None:
        super().__init__(parent, corner_radius=24, fg_color=CARD_COLOR)
        self._on_submit = on_submit

        customtkinter.CTkLabel(
            self,
            text="Estender tempo",
            font=("Arial", 34, "bold"),
            justify="center",
            wraplength=700,
        ).pack(pady=(36, 8))
        customtkinter.CTkLabel(
            self,
            text=(
                "Digite a senha de autorização e por quantos minutos o uso "
                "pode continuar."
            ),
            font=("Arial", 18),
            text_color=TEXT_MUTED,
            justify="center",
            wraplength=700,
        ).pack(pady=(0, 16))

        form = customtkinter.CTkFrame(self, fg_color="transparent")
        form.pack(pady=(0, 8))
        customtkinter.CTkLabel(
            form,
            text="Senha de autorização",
            font=("Arial", 18),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._password = customtkinter.CTkEntry(
            form,
            width=300,
            height=44,
            font=("Arial", 20),
            show="*",
        )
        self._password.grid(row=1, column=0, sticky="w", pady=(0, 10))

        customtkinter.CTkLabel(
            form,
            text="Minutos de extensão",
            font=("Arial", 18),
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))
        self._minutes = customtkinter.CTkEntry(
            form,
            width=160,
            height=44,
            font=("Arial", 20),
            justify="center",
            placeholder_text="minutos",
        )
        self._minutes.grid(row=3, column=0, sticky="w")

        self._error = customtkinter.CTkLabel(
            self,
            text="",
            font=("Arial", 16),
            text_color=ERROR_COLOR,
            justify="center",
            wraplength=700,
        )
        self._error.pack(pady=(0, 10))

        buttons = customtkinter.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=(0, 20))
        customtkinter.CTkButton(
            buttons,
            text="Cancelar",
            width=150,
            height=52,
            font=("Arial", 18),
            fg_color="transparent",
            border_width=1,
            text_color="#333333",
            command=on_cancel,
        ).pack(side="left", padx=(0, 12))
        customtkinter.CTkButton(
            buttons,
            text="Confirmar",
            width=170,
            height=52,
            font=("Arial", 18),
            command=self._submit,
        ).pack(side="left")

        self._password.bind("<Return>", lambda _event: self._submit())
        self._minutes.bind("<Return>", lambda _event: self._submit())
        self.after(100, self._focus_password)

    def _focus_password(self) -> None:
        if not self.winfo_exists():
            return
        try:
            self._password.focus_set()
        except tk.TclError:
            pass

    def _show_error(self, message: str) -> None:
        self._error.configure(text=message)

    def _submit(self) -> None:
        if not self.winfo_exists():
            return
        raw_minutes = self._minutes.get().strip()
        try:
            minutes = int(raw_minutes)
        except ValueError:
            self._show_error("Digite um número inteiro de minutos.")
            return
        if not EXTENSION_MINUTES_MIN <= minutes <= EXTENSION_MINUTES_MAX:
            self._show_error(
                f"Os minutos devem ficar entre {EXTENSION_MINUTES_MIN} e "
                f"{EXTENSION_MINUTES_MAX}."
            )
            return
        password = self._password.get()
        if not password:
            self._show_error("Digite a senha de autorização.")
            return
        error = self._on_submit(password, minutes)
        if error and self.winfo_exists():
            self._show_error(error)
