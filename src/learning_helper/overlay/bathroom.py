from __future__ import annotations

from collections.abc import Callable

from learning_helper.overlay.countdown import CountdownPanel
from learning_helper.overlay.images import load_bathroom_image


class BathroomPanel(CountdownPanel):
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
        super().__init__(
            parent,
            seconds=seconds,
            title="Hora de ir ao banheiro!",
            on_finished=on_finished,
            image=load_bathroom_image(),
        )
