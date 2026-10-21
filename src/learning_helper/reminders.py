"""Lógica do lembrete de banheiro (sem Tk, para ser testável)."""

from __future__ import annotations

from datetime import datetime

from learning_helper.config import BATHROOM_INTERVAL_SECONDS


def seconds_until_next(
    last_at: datetime | None,
    now: datetime,
    interval_seconds: int = BATHROOM_INTERVAL_SECONDS,
) -> int:
    """Segundos até o próximo lembrete (0 quando já venceu)."""
    if interval_seconds <= 0:
        return 0
    if last_at is None:
        return interval_seconds
    elapsed = (now - last_at).total_seconds()
    remaining = interval_seconds - elapsed
    if remaining <= 0:
        return 0
    # Se o relógio andou para trás, não passa de um intervalo inteiro.
    return min(interval_seconds, int(remaining))


def format_countdown(seconds: int) -> str:
    """Formata a contagem como MM:SS, nunca negativa."""
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"
