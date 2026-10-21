from __future__ import annotations

from collections.abc import Callable

import customtkinter

from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
from learning_helper.config import ADULT_SHORTCUT, FEEDBACK_MS
from learning_helper.overlay.images import color_swatch, rgb_to_hex


class ChallengeHost(customtkinter.CTkToplevel):
    def __init__(
        self,
        parent,
        spec: ChallengeSpec,
        *,
        on_answer: Callable[[str], None],
        on_adult_pause: Callable[[], None],
        geometry: tuple[int, int, int, int],
    ) -> None:
        super().__init__(parent)
        self._spec = spec
        self._on_answer = on_answer
        self._answered = False
        width, height, x, y = geometry

        customtkinter.set_appearance_mode("light")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.title("Desafio")
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.bind(ADULT_SHORTCUT, lambda _event: on_adult_pause())

        self._btn_height = int(height * 0.32)
        self._btn_width = int(width * 0.18)
        self._status = customtkinter.CTkLabel(
            self,
            text=spec.prompt,
            font=("Arial", 32),
            pady=36,
            wraplength=width - 80,
        )
        self._status.pack()
        self._buttons: list[customtkinter.CTkButton] = []
        self._place_choices(width, height)
        self.deiconify()
        self.lift()
        self.focus_force()

    def _place_choices(self, window_width: int, window_height: int) -> None:
        count = len(self._spec.choices)
        gap = (window_width - (self._btn_width * count)) / (count + 1)
        x = gap
        y = (window_height / 2) - (self._btn_height / 2)
        for choice in self._spec.choices:
            button = self._make_button(choice)
            button.place(x=x, y=y)
            self._buttons.append(button)
            x += self._btn_width + gap

    def _make_button(self, choice: ChallengeChoice) -> customtkinter.CTkButton:
        kwargs: dict = {
            "text": choice.label if choice.rgb is None else "",
            "command": lambda selected=choice.id: self._choose(selected),
            "width": self._btn_width,
            "height": self._btn_height,
            "font": ("Arial", 22),
        }
        if choice.rgb is not None:
            image = color_swatch(choice.rgb, self._btn_width, self._btn_height)
            kwargs["image"] = customtkinter.CTkImage(
                light_image=image,
                size=(self._btn_width, self._btn_height),
            )
            kwargs["fg_color"] = rgb_to_hex(choice.rgb)
            kwargs["hover_color"] = rgb_to_hex(choice.rgb)
            kwargs["text"] = ""
        return customtkinter.CTkButton(self, **kwargs)

    def _choose(self, selected: str) -> None:
        if self._answered:
            return
        self._answered = True
        for button in self._buttons:
            button.configure(state="disabled")
        correct = selected == self._spec.correct_id
        self.configure(fg_color="#d6f5d6" if correct else "#f8d4d4")
        self._status.configure(text="Certo!" if correct else "Quase! Olhe com calma da próxima vez.")
        self.after(FEEDBACK_MS, lambda: self._finish(selected))

    def _finish(self, selected: str) -> None:
        self._on_answer(selected)
        self.destroy()
