from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter

from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
from learning_helper.config import FEEDBACK_MS
from learning_helper.overlay.images import color_swatch, rgb_to_hex

MAX_COLUMNS = 4
SWATCH_WIDTH = 160
SWATCH_HEIGHT = 90
CARD_COLOR = "#f7f7f7"
CORRECT_COLOR = "#d6f5d6"
WRONG_COLOR = "#f8d4d4"
HINT_COLOR = "#555555"


class ChallengePanel(customtkinter.CTkFrame):
    """Desafio renderizado dentro da janela do overlay (sem toplevel própria)."""

    def __init__(
        self,
        parent,
        spec: ChallengeSpec,
        *,
        on_answer: Callable[[ChallengeSpec, str], None],
        feedback_ms: int = FEEDBACK_MS,
    ) -> None:
        super().__init__(parent, corner_radius=24, fg_color=CARD_COLOR)
        self._spec = spec
        self._on_answer = on_answer
        self._feedback_ms = feedback_ms
        self._answered = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._status = customtkinter.CTkLabel(
            self,
            text=spec.prompt,
            font=("Arial", 28),
            justify="center",
            wraplength=600,
        )
        self._status.grid(row=0, column=0, sticky="ew", padx=32, pady=(32, 16))

        self._choices_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self._choices_frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 28))

        self._buttons: list[customtkinter.CTkButton] = []
        self._entry: customtkinter.CTkEntry | None = None
        self._ok_button: customtkinter.CTkButton | None = None
        self._hint: customtkinter.CTkLabel | None = None
        self._place_choices()
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event) -> None:
        self._status.configure(wraplength=max(240, event.width - 64))

    def _place_choices(self) -> None:
        if self._spec.input_mode == "text":
            self._place_text_input()
            return
        count = len(self._spec.choices)
        columns = min(count, MAX_COLUMNS) or 1
        rows = -(-count // columns)

        for column in range(columns):
            self._choices_frame.grid_columnconfigure(column, weight=1, uniform="choice")
        for row in range(rows):
            self._choices_frame.grid_rowconfigure(row, weight=1, uniform="choice")

        for index, choice in enumerate(self._spec.choices):
            button = self._make_button(choice)
            button.grid(
                row=index // columns,
                column=index % columns,
                sticky="nsew",
                padx=8,
                pady=8,
            )
            self._buttons.append(button)

    def _place_text_input(self) -> None:
        """Campo de resposta digitada + botão OK (módulo de comparação)."""
        self._choices_frame.grid_columnconfigure(0, weight=1)
        self._choices_frame.grid_rowconfigure(0, weight=1)

        row = customtkinter.CTkFrame(self._choices_frame, fg_color="transparent")
        row.grid(row=0, column=0)

        self._entry = customtkinter.CTkEntry(
            row,
            width=220,
            height=64,
            font=("Arial", 28),
            justify="center",
            placeholder_text="Número",
        )
        self._entry.pack(side="left", padx=(0, 12))
        self._entry.bind("<Return>", self._on_return)

        self._ok_button = customtkinter.CTkButton(
            row,
            text="OK",
            width=120,
            height=64,
            font=("Arial", 24),
            command=self._submit_text,
        )
        self._ok_button.pack(side="left")

        self._hint = customtkinter.CTkLabel(
            self._choices_frame,
            text="",
            font=("Arial", 16),
            text_color=HINT_COLOR,
        )
        self._hint.grid(row=1, column=0, pady=(6, 0))
        self.after(100, self._focus_entry)

    def _focus_entry(self) -> None:
        if not self.winfo_exists() or self._entry is None:
            return
        try:
            self._entry.focus_set()
        except tk.TclError:
            pass

    def _on_return(self, _event=None) -> None:
        self._submit_text()

    def _show_hint(self, text: str) -> None:
        if self._hint is not None:
            self._hint.configure(text=text)

    def _submit_text(self) -> None:
        if self._answered or self._entry is None:
            return
        raw = self._entry.get().strip()
        if not raw:
            self._show_hint("Digite um número.")
            return
        try:
            int(raw)
        except ValueError:
            self._show_hint("Digite apenas o número.")
            return
        self._answered = True
        self._entry.configure(state="disabled")
        if self._ok_button is not None:
            self._ok_button.configure(state="disabled")
        self._show_hint("")
        self._settle(raw, self._spec.is_correct(raw))

    def _make_button(self, choice: ChallengeChoice) -> customtkinter.CTkButton:
        kwargs: dict = {
            "command": lambda selected=choice.id: self._choose(selected),
            "font": ("Arial", 24),
            "width": SWATCH_WIDTH,
            "height": 80,
        }
        if choice.rgb is not None:
            image = color_swatch(choice.rgb, SWATCH_WIDTH, SWATCH_HEIGHT)
            kwargs["image"] = customtkinter.CTkImage(
                light_image=image,
                size=(SWATCH_WIDTH, SWATCH_HEIGHT),
            )
            kwargs["fg_color"] = rgb_to_hex(choice.rgb)
            kwargs["hover_color"] = rgb_to_hex(choice.rgb)
            kwargs["text"] = ""
        else:
            kwargs["text"] = choice.label
        return customtkinter.CTkButton(self._choices_frame, **kwargs)

    def _settle(self, given: str, correct: bool) -> None:
        self.configure(fg_color=CORRECT_COLOR if correct else WRONG_COLOR)
        self._status.configure(
            text="Certo!" if correct else "Quase! Olhe com calma da próxima vez."
        )
        self.after(self._feedback_ms, lambda: self._finish(given))

    def _choose(self, selected: str) -> None:
        if self._answered:
            return
        self._answered = True
        for button in self._buttons:
            button.configure(state="disabled")
        self._settle(selected, self._spec.is_correct(selected))

    def _finish(self, selected: str) -> None:
        if not self.winfo_exists():
            return
        self._on_answer(self._spec, selected)
