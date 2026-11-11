from datetime import datetime

from learning_helper.persistence.db import Store
from learning_helper.settings import Settings
from learning_helper.usage import DailyUsage, format_duration, local_day_key


class FakeClock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment
        self.monotonic_value = 0.0

    def now(self) -> datetime:
        return self.moment

    def monotonic(self) -> float:
        return self.monotonic_value


def test_format_duration() -> None:
    assert format_duration(0) == "0 min"
    assert format_duration(90) == "1 min"
    assert format_duration(3600) == "1 h"
    assert format_duration(5400) == "1 h 30 min"


def test_local_day_key_uses_local_date() -> None:
    assert local_day_key(datetime(2026, 10, 25, 23, 59)) == "2026-10-25"


def test_daily_usage_counts_only_while_active(store: Store) -> None:
    clock = FakeClock(datetime(2026, 10, 25, 10, 0))
    usage = DailyUsage(
        store,
        2 * 60 * 60,
        now=clock.now,
        monotonic=clock.monotonic,
        flush_seconds=30,
    )

    clock.monotonic_value += 10
    assert usage.tick(active=False) is False
    assert usage.used_seconds == 0

    clock.monotonic_value += 12
    usage.tick(active=True)
    assert usage.used_seconds == 12
    assert store.get_daily_usage(usage.day) == 0

    clock.monotonic_value += 20
    usage.tick(active=True)
    assert usage.used_seconds == 32
    assert store.get_daily_usage(usage.day) == 32


def test_daily_usage_is_loaded_after_restart(store: Store) -> None:
    clock = FakeClock(datetime(2026, 10, 25, 10, 0))
    usage = DailyUsage(
        store,
        2 * 60 * 60,
        now=clock.now,
        monotonic=clock.monotonic,
        flush_seconds=1,
    )
    clock.monotonic_value += 45
    usage.tick(active=True)
    usage.flush()

    restarted = DailyUsage(
        store,
        2 * 60 * 60,
        now=clock.now,
        monotonic=clock.monotonic,
    )

    assert restarted.used_seconds == 45
    assert restarted.total_allowed_seconds == 2 * 60 * 60
    assert restarted.remaining_seconds == 2 * 60 * 60 - 45
    assert restarted.is_exhausted is False


def test_extension_is_in_memory_and_can_be_exhausted(store: Store) -> None:
    clock = FakeClock(datetime(2026, 10, 25, 10, 0))
    store.add_daily_usage(usage_day := local_day_key(clock.now()), 2 * 60 * 60)
    usage = DailyUsage(
        store,
        2 * 60 * 60,
        now=clock.now,
        monotonic=clock.monotonic,
        flush_seconds=1,
    )

    assert usage.is_exhausted is True
    usage.extend(5)
    assert usage.extension_seconds == 5 * 60
    assert usage.remaining_seconds == 5 * 60
    assert usage.is_exhausted is False

    clock.monotonic_value += 5 * 60
    usage.tick(active=True)

    assert usage.is_exhausted is True
    assert store.get_daily_usage(usage_day) == 2 * 60 * 60 + 5 * 60

    restarted = DailyUsage(
        store,
        2 * 60 * 60,
        now=clock.now,
        monotonic=clock.monotonic,
    )
    assert restarted.extension_seconds == 0
    assert restarted.is_exhausted is True


def test_extension_grants_requested_time_above_daily_limit(store: Store) -> None:
    """Depois de reiniciar, a extensão vale a partir do uso já acumulado."""
    clock = FakeClock(datetime(2026, 10, 25, 10, 0))
    day = local_day_key(clock.now())
    used = 6 * 60 * 60 + 30 * 60
    limit = 3 * 60 * 60 + 30 * 60
    store.add_daily_usage(day, used)

    usage = DailyUsage(
        store,
        limit,
        now=clock.now,
        monotonic=clock.monotonic,
        flush_seconds=1,
    )

    assert usage.total_allowed_seconds == used
    assert usage.is_exhausted is True

    usage.extend(30)
    assert usage.extension_seconds == 30 * 60
    assert usage.remaining_seconds == 30 * 60
    assert usage.is_exhausted is False

    clock.monotonic_value += 30 * 60
    usage.tick(active=True)
    assert usage.is_exhausted is True
    assert store.get_daily_usage(day) == used + 30 * 60

    restarted = DailyUsage(
        store,
        limit,
        now=clock.now,
        monotonic=clock.monotonic,
    )
    assert restarted.extension_seconds == 0
    assert restarted.is_exhausted is True

    restarted.extend(30)
    assert restarted.remaining_seconds == 30 * 60
    assert restarted.is_exhausted is False


def test_extension_grants_requested_time_after_usage_overruns(store: Store) -> None:
    clock = FakeClock(datetime(2026, 10, 25, 10, 0))
    store.add_daily_usage(local_day_key(clock.now()), 2 * 60 * 60)
    usage = DailyUsage(
        store,
        2 * 60 * 60,
        now=clock.now,
        monotonic=clock.monotonic,
        flush_seconds=1,
    )
    assert usage.is_exhausted is True
    usage.extend(5)

    # A pausa do adulto libera a tela e o tempo continua contando; a extensão
    # anterior pode ser consumida e ultrapassada antes do próximo pedido.
    clock.monotonic_value += 10 * 60
    usage.tick(active=True)
    assert usage.used_seconds == 2 * 60 * 60 + 10 * 60
    assert usage.is_exhausted is True

    usage.extend(5)
    assert usage.extension_seconds == 10 * 60
    assert usage.remaining_seconds == 5 * 60
    assert usage.is_exhausted is False


def test_extension_adds_to_remaining_time(store: Store) -> None:
    clock = FakeClock(datetime(2026, 10, 25, 10, 0))
    store.add_daily_usage(local_day_key(clock.now()), 60 * 60)
    usage = DailyUsage(
        store,
        2 * 60 * 60,
        now=clock.now,
        monotonic=clock.monotonic,
    )

    assert usage.remaining_seconds == 60 * 60
    usage.extend(15)
    assert usage.extension_seconds == 15 * 60
    assert usage.remaining_seconds == 75 * 60


def test_extension_is_session_only_and_does_not_change_daily_limit(
    store: Store,
) -> None:
    limit = 2 * 60 * 60
    store.save_settings(Settings(daily_usage_limit_seconds=limit))
    clock = FakeClock(datetime(2026, 10, 25, 10, 0))
    day = local_day_key(clock.now())
    store.add_daily_usage(day, limit)

    usage = DailyUsage(
        store,
        limit,
        now=clock.now,
        monotonic=clock.monotonic,
        flush_seconds=1,
    )

    assert usage.used_seconds == limit
    assert usage.extension_seconds == 0
    assert usage.total_allowed_seconds == limit
    assert usage.remaining_seconds == 0
    assert usage.is_exhausted is True

    usage.extend(30)

    assert usage.extension_seconds == 30 * 60
    assert usage.total_allowed_seconds == limit + 30 * 60
    assert usage.remaining_seconds == 30 * 60
    assert usage.is_exhausted is False
    # A extensão só vira tempo usado depois de ser consumida.
    assert store.get_daily_usage(day) == limit
    assert store.get_settings().daily_usage_limit_seconds == limit

    clock.monotonic_value += 30 * 60
    usage.tick(active=True)

    assert usage.used_seconds == limit + 30 * 60
    assert store.get_daily_usage(day) == limit + 30 * 60
    assert usage.remaining_seconds == 0
    assert usage.is_exhausted is True

    # Reiniciar o app/computador descarta a extensão, mas mantém o uso no banco.
    restart_clock = FakeClock(clock.moment)
    restarted = DailyUsage(
        store,
        limit,
        now=restart_clock.now,
        monotonic=restart_clock.monotonic,
    )

    assert restarted.extension_seconds == 0
    assert restarted.daily_limit_seconds == limit
    assert restarted.used_seconds == limit + 30 * 60
    assert restarted.total_allowed_seconds == limit + 30 * 60
    assert restarted.remaining_seconds == 0
    assert restarted.is_exhausted is True
    assert store.get_settings().daily_usage_limit_seconds == limit
    assert format_duration(restarted.daily_limit_seconds) == "2 h"
    assert format_duration(restarted.used_seconds) == "2 h 30 min"

    restarted.extend(30)

    assert restarted.extension_seconds == 30 * 60
    assert restarted.total_allowed_seconds == limit + 60 * 60
    assert restarted.remaining_seconds == 30 * 60
    assert restarted.is_exhausted is False
    assert store.get_settings().daily_usage_limit_seconds == limit
    assert store.get_daily_usage(day) == limit + 30 * 60


def test_midnight_resets_usage_and_extension(store: Store) -> None:
    clock = FakeClock(datetime(2026, 10, 25, 23, 59))
    store.add_daily_usage(local_day_key(clock.now()), 100)
    usage = DailyUsage(
        store,
        2 * 60 * 60,
        now=clock.now,
        monotonic=clock.monotonic,
        flush_seconds=1,
    )
    usage.extend(5)

    clock.moment = datetime(2026, 10, 26, 0, 0, 1)
    clock.monotonic_value += 10

    assert usage.tick(active=True) is True
    assert usage.day == "2026-10-26"
    assert usage.used_seconds == 0
    assert usage.extension_seconds == 0
