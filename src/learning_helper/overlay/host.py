from __future__ import annotations

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


class ChallengePanel(customtkinter.CTkFrame):
    """Desafio renderizado dentro da janela do overlay (sem toplevel própria)."""

    def __init__(
        self,
        parent,
        spec: ChallengeSpec,
        *,
        on_answer: Callable[[ChallengeSpec, str], None],
    ) -> None:
        super().__init__(parent, corner_radius=24, fg_color=CARD_COLOR)
        self._spec = spec
        self._on_answer = on_answer
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
        self._place_choices()
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event) -> None:
        self._status.configure(wraplength=max(240, event.width - 64))

    def _place_choices(self) -> None:
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

    def _choose(self, selected: str) -> None:
        if self._answered:
            return
        self._answered = True
        for button in self._buttons:
            button.configure(state="disabled")
        correct = selected == self._spec.correct_id
        self.configure(fg_color=CORRECT_COLOR if correct else WRONG_COLOR)
        self._status.configure(
            text="Certo!" if correct else "Quase! Olhe com calma da próxima vez."
        )
        self.after(FEEDBACK_MS, lambda: self._finish(selected))

    def _finish(self, selected: str) -> None:
        if not self.winfo_exists():
            return
        self._on_answer(self._spec, selected)
