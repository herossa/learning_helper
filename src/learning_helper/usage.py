"""Contagem do tempo diário de uso, sem dependência de Tk."""

from __future__ import annotations

import time
from datetime import datetime

from learning_helper.config import DAILY_USAGE_FLUSH_SECONDS
from learning_helper.persistence.db import Store


def local_day_key(moment: datetime | None = None) -> str:
    """Data local usada para reiniciar a contagem à meia-noite."""
    return (moment or datetime.now()).date().isoformat()


def format_duration(seconds: int) -> str:
    """Formata segundos como "2 h", "1 h 30 min" ou "45 min"."""
    total_minutes = max(0, int(seconds)) // 60
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours} h {minutes} min"
    if hours:
        return f"{hours} h"
    return f"{minutes} min"


class DailyUsage:
    """Acumula o tempo com o app rodando e persiste por dia local.

    A extensão fica apenas em memória: ela vale até o app/computador
    reiniciar ou até a virada do dia, sem alterar o limite configurado.
    O teto efetivo parte do maior valor entre o limite configurado e o tempo
    já usado e cresce pelos minutos pedidos. Assim, cada extensão libera os
    minutos solicitados a partir do uso acumulado, mesmo que ele já tenha
    passado do limite (por exemplo, depois de reiniciar o computador).
    """

    def __init__(
        self,
        store: Store,
        daily_limit_seconds: int,
        *,
        now=datetime.now,
        monotonic=time.monotonic,
        flush_seconds: int = DAILY_USAGE_FLUSH_SECONDS,
    ) -> None:
        self._store = store
        self.daily_limit_seconds = max(0, int(daily_limit_seconds))
        self._now = now
        self._monotonic = monotonic
        self._flush_seconds = max(1, int(flush_seconds))
        self._day = local_day_key(self._now())
        self._used_seconds = float(self._store.get_daily_usage(self._day))
        self._pending_seconds = 0.0
        self._extension_seconds = 0
        self._allowed_seconds = max(self.daily_limit_seconds, int(self._used_seconds))
        self._last_monotonic = self._monotonic()

    @property
    def day(self) -> str:
        return self._day

    @property
    def used_seconds(self) -> int:
        return int(self._used_seconds + self._pending_seconds)

    @property
    def extension_seconds(self) -> int:
        return self._extension_seconds

    @property
    def total_allowed_seconds(self) -> int:
        return self._allowed_seconds

    @property
    def remaining_seconds(self) -> int:
        return max(0, self.total_allowed_seconds - self.used_seconds)

    @property
    def is_exhausted(self) -> bool:
        return self.used_seconds >= self.total_allowed_seconds

    def tick(self, *, active: bool) -> bool:
        """Atualiza a contagem. Devolve True quando o dia virou."""
        now = self._now()
        day = local_day_key(now)
        current = self._monotonic()
        if day != self._day:
            self.flush()
            self._day = day
            self._used_seconds = float(self._store.get_daily_usage(day))
            self._pending_seconds = 0.0
            self._extension_seconds = 0
            self._allowed_seconds = max(
                self.daily_limit_seconds, int(self._used_seconds)
            )
            self._last_monotonic = current
            return True

        elapsed = max(0.0, current - self._last_monotonic)
        self._last_monotonic = current
        if active and elapsed > 0:
            self._pending_seconds += elapsed
            if self._pending_seconds >= self._flush_seconds:
                self.flush()
        return False

    def flush(self) -> None:
        """Grava no SQLite os segundos inteiros acumulados."""
        seconds = int(self._pending_seconds)
        if seconds <= 0:
            return
        self._store.add_daily_usage(self._day, seconds)
        self._used_seconds += seconds
        self._pending_seconds -= seconds

    def extend(self, minutes: int) -> None:
        """Libera os minutos pedidos a partir do uso acumulado."""
        value = int(minutes)
        if value <= 0:
            raise ValueError("A extensão deve ter pelo menos 1 minuto.")
        requested = value * 60
        self._allowed_seconds = (
            max(self._allowed_seconds, self.used_seconds) + requested
        )
        self._extension_seconds += requested
