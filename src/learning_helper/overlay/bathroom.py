from __future__ import annotations

from collections.abc import Callable

import customtkinter

from learning_helper import reminders
from learning_helper.overlay.images import load_bathroom_image

CARD_COLOR = "#f7f7f7"
IMAGE_SIZE = 200


class BathroomPanel(customtkinter.CTkFrame):
    """Tela do lembrete de banheiro: informa e conta os segundos restantes.

    Não tem nada para responder: apenas bloqueia a tela e fecha sozinha.
    """

    def __init__(
        self,
        parent,
        *,
        seconds: int,
        on_finished: Callable[[], None],
    ) -> None:
        super().__init__(parent, corner_radius=24, fg_color=CARD_COLOR)
        self._remaining = max(0, int(seconds))
        self._on_finished = on_finished
        self._job: str | None = None

        self._image = customtkinter.CTkImage(
            light_image=load_bathroom_image(),
            size=(IMAGE_SIZE, IMAGE_SIZE),
        )
        title = customtkinter.CTkLabel(
            self,
            text="Hora de ir ao banheiro!",
            font=("Arial", 34),
            justify="center",
            wraplength=700,
        )
        title.pack(pady=(36, 8))
        image_label = customtkinter.CTkLabel(self, image=self._image, text="")
        image_label.pack(pady=8)
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
