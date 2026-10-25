from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter

from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
from learning_helper.config import ANSWER_UNLOCK_DELAY_MS, FEEDBACK_MS
from learning_helper.overlay.images import color_swatch, rgb_to_hex

MAX_COLUMNS = 4
SWATCH_WIDTH = 160
SWATCH_HEIGHT = 90
CARD_COLOR = "#f7f7f7"
CORRECT_COLOR = "#d6f5d6"
WRONG_COLOR = "#f8d4d4"
HINT_COLOR = "#555555"
GUIDANCE_TEXT = "Leia com atenção antes de responder."


class ChallengePanel(customtkinter.CTkFrame):
    """Desafio renderizado dentro da janela do overlay (sem toplevel própria)."""

    def __init__(
        self,
        parent,
        spec: ChallengeSpec,
        *,
        on_answer: Callable[[ChallengeSpec, str], None],
        feedback_ms: int = FEEDBACK_MS,
        answer_delay_ms: int = ANSWER_UNLOCK_DELAY_MS,
    ) -> None:
        super().__init__(parent, corner_radius=24, fg_color=CARD_COLOR)
        self._spec = spec
        self._on_answer = on_answer
        self._feedback_ms = feedback_ms
        self._answer_delay_ms = max(0, int(answer_delay_ms))
        self._answered = False
        self._locked = self._answer_delay_ms > 0
        self._unlock_job: str | None = None
        self._focus_job: str | None = None
        self._feedback_job: str | None = None

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
        self._choices_frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 12))

        self._guidance = customtkinter.CTkLabel(
            self,
            text=GUIDANCE_TEXT,
            font=("Arial", 16),
            text_color=HINT_COLOR,
        )
        self._guidance.grid(row=2, column=0, pady=(0, 24))

        self._buttons: list[customtkinter.CTkButton] = []
        self._entry: customtkinter.CTkEntry | None = None
        self._ok_button: customtkinter.CTkButton | None = None
        self._hint: customtkinter.CTkLabel | None = None
        self._place_choices()
        if self._locked:
            self._set_answers_enabled(False)
            self._unlock_job = self.after(
                self._answer_delay_ms, self._unlock_answers
            )
        elif self._entry is not None:
            self._schedule_focus()
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event) -> None:
        self._status.configure(wraplength=max(240, event.width - 64))

    def _set_answers_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in self._buttons:
            button.configure(state=state)
        if self._entry is not None:
            self._entry.configure(state=state)
        if self._ok_button is not None:
            self._ok_button.configure(state=state)

    def _unlock_answers(self) -> None:
        self._unlock_job = None
        if not self.winfo_exists():
            return
        self._locked = False
        if self._answered:
            return
        self._set_answers_enabled(True)
        if self._entry is not None:
            self._schedule_focus()

    def _schedule_focus(self) -> None:
        self._focus_job = self.after(50, self._focus_entry)

    def _cancel_job(self, attribute: str) -> None:
        job = getattr(self, attribute)
        if job is None:
            return
        try:
            self.after_cancel(job)
        except tk.TclError:
            pass
        setattr(self, attribute, None)

    def destroy(self) -> None:
        for attribute in ("_unlock_job", "_focus_job", "_feedback_job"):
            self._cancel_job(attribute)
        super().destroy()

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

    def _focus_entry(self) -> None:
        self._focus_job = None
        if self._locked or not self.winfo_exists() or self._entry is None:
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
        if self._locked or self._answered or self._entry is None:
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
        self._feedback_job = self.after(
            self._feedback_ms, lambda: self._finish(given)
        )

    def _choose(self, selected: str) -> None:
        if self._locked or self._answered:
            return
        self._answered = True
        for button in self._buttons:
            button.configure(state="disabled")
        self._settle(selected, self._spec.is_correct(selected))

    def _finish(self, selected: str) -> None:
        self._feedback_job = None
        if not self.winfo_exists():
            return
        self._on_answer(self._spec, selected)
