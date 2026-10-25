from __future__ import annotations

from collections.abc import Callable

import customtkinter

from learning_helper import reminders

CARD_COLOR = "#f7f7f7"
WRONG_CARD_COLOR = "#f8d4d4"
SUBTITLE_COLOR = "#555555"
IMAGE_SIZE = 200


class CountdownPanel(customtkinter.CTkFrame):
    """Tela de espera com contagem regressiva e nada para responder.

    Usada pelo lembrete de banheiro e pela espera após uma resposta errada.
    """

    def __init__(
        self,
        parent,
        *,
        seconds: int,
        title: str,
        on_finished: Callable[[], None],
        subtitle: str = "",
        image=None,
        fg_color: str = CARD_COLOR,
    ) -> None:
        super().__init__(parent, corner_radius=24, fg_color=fg_color)
        self._remaining = max(0, int(seconds))
        self._on_finished = on_finished
        self._job: str | None = None

        customtkinter.CTkLabel(
            self,
            text=title,
            font=("Arial", 34),
            justify="center",
            wraplength=700,
        ).pack(pady=(36, 8))

        self._image = None
        if image is not None:
            self._image = customtkinter.CTkImage(
                light_image=image,
                size=(IMAGE_SIZE, IMAGE_SIZE),
            )
            customtkinter.CTkLabel(self, image=self._image, text="").pack(pady=8)

        if subtitle:
            customtkinter.CTkLabel(
                self,
                text=subtitle,
                font=("Arial", 18),
                text_color=SUBTITLE_COLOR,
                justify="center",
                wraplength=700,
            ).pack(pady=(4, 0))

        self._timer = customtkinter.CTkLabel(
            self,
            text=reminders.format_countdown(self._remaining),
            font=("Arial", 56, "bold"),
        )
        self._timer.pack(pady=(8, 36))
        self._tick()

    def _tick(self) -> None:
        if not self.winfo_exists():
            return
        self._timer.configure(text=reminders.format_countdown(self._remaining))
        if self._remaining <= 0:
            self._on_finished()
            return
        self._remaining -= 1
        self._job = self.after(1000, self._tick)

    def cancel(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
