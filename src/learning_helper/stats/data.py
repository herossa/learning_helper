"""Consultas de leitura para as estatísticas (sem depender de Streamlit)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from learning_helper.config import MODULE_ORDER
from learning_helper.settings import Settings


class StatsDataError(RuntimeError):
    """Banco ausente, ilegível ou sem as tabelas esperadas."""


@dataclass(frozen=True)
class AttemptRecord:
    created_at: datetime
    module_id: str
    level: int
    is_correct: bool
    prompt: str
    given_answer: str
    correct_answer: str


@dataclass(frozen=True)
class ProfileSummary:
    levels: dict[str, int]
    unlocked: tuple[str, ...]
    enabled_modules: tuple[str, ...]


@dataclass(frozen=True)
class Kpis:
    attempts: int
    correct: int
    accuracy: float
    active_days: int


@dataclass(frozen=True)
class ModuleSummary:
    module_id: str
    attempts: int
    correct: int
    accuracy: float
    last_level: int


@dataclass(frozen=True)
class DailySummary:
    day: date
    attempts: int
    correct: int
    accuracy: float


@dataclass(frozen=True)
class LevelSummary:
    module_id: str
    level: int
    attempts: int
    correct: int
    accuracy: float


def _readonly_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise StatsDataError(f"Banco não encontrado em {db_path}.")
    uri = db_path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def _parse_datetime(raw: str) -> datetime:
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _to_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def load_attempts(
    db_path: Path,
    *,
    since: datetime | None = None,
    module_ids: tuple[str, ...] | None = None,
) -> list[AttemptRecord]:
    if module_ids is not None and not module_ids:
        return []
    sql = """
        SELECT created_at, module_id, level, is_correct, prompt,
               given_answer, correct_answer
        FROM attempts
    """
    clauses: list[str] = []
    parameters: list[object] = []
    if since is not None:
        clauses.append("created_at >= ?")
        parameters.append(_to_iso(since))
    if module_ids is not None:
        placeholders = ", ".join("?" for _ in module_ids)
        clauses.append(f"module_id IN ({placeholders})")
        parameters.extend(module_ids)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"

    connection = None
    try:
        connection = _readonly_connection(db_path)
        rows = connection.execute(sql, parameters).fetchall()
    except sqlite3.DatabaseError as exc:
        raise StatsDataError(f"Não foi possível ler o banco: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
    return [
        AttemptRecord(
            created_at=_parse_datetime(row["created_at"]),
            module_id=row["module_id"],
            level=int(row["level"]),
            is_correct=bool(row["is_correct"]),
            prompt=row["prompt"],
            given_answer=row["given_answer"],
            correct_answer=row["correct_answer"],
        )
        for row in rows
    ]


def load_profile(db_path: Path) -> ProfileSummary | None:
    connection = None
    try:
        connection = _readonly_connection(db_path)
        profile_row = connection.execute(
            "SELECT levels_json, unlocked_modules_json FROM profile WHERE id = 1"
        ).fetchone()
        settings_row = connection.execute(
            "SELECT values_json FROM settings WHERE id = 1"
        ).fetchone()
    except sqlite3.DatabaseError as exc:
        raise StatsDataError(f"Não foi possível ler o banco: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
    if profile_row is None:
        return None
    settings = Settings.from_json(
        settings_row["values_json"] if settings_row is not None else None
    )
    try:
        levels = json.loads(profile_row["levels_json"])
        unlocked = tuple(json.loads(profile_row["unlocked_modules_json"]))
        levels = {module: int(levels.get(module, 1)) for module in MODULE_ORDER}
    except (TypeError, ValueError) as exc:
        raise StatsDataError(f"Perfil inválido no banco: {exc}") from exc
    return ProfileSummary(
        levels=levels,
        unlocked=unlocked,
        enabled_modules=settings.enabled_modules,
    )


def kpis(records: list[AttemptRecord]) -> Kpis:
    attempts = len(records)
    correct = sum(1 for record in records if record.is_correct)
    active_days = len({_local_day(record.created_at) for record in records})
    return Kpis(
        attempts=attempts,
        correct=correct,
        accuracy=correct / attempts if attempts else 0.0,
        active_days=active_days,
    )


def by_module(records: list[AttemptRecord]) -> list[ModuleSummary]:
    summaries: list[ModuleSummary] = []
    modules = list(MODULE_ORDER)
    modules += sorted(
        {record.module_id for record in records} - set(MODULE_ORDER)
    )
    for module in modules:
        subset = [record for record in records if record.module_id == module]
        if not subset:
            continue
        correct = sum(1 for record in subset if record.is_correct)
        summaries.append(
            ModuleSummary(
                module_id=module,
                attempts=len(subset),
                correct=correct,
                accuracy=correct / len(subset),
                last_level=subset[-1].level,
            )
        )
    return summaries


def by_day(records: list[AttemptRecord]) -> list[DailySummary]:
    grouped: dict[date, list[AttemptRecord]] = {}
    for record in records:
        grouped.setdefault(_local_day(record.created_at), []).append(record)
    summaries = []
    for day in sorted(grouped):
        subset = grouped[day]
        correct = sum(1 for record in subset if record.is_correct)
        summaries.append(
            DailySummary(
                day=day,
                attempts=len(subset),
                correct=correct,
                accuracy=correct / len(subset),
            )
        )
    return summaries


def by_level(records: list[AttemptRecord]) -> list[LevelSummary]:
    grouped: dict[tuple[str, int], list[AttemptRecord]] = {}
    for record in records:
        grouped.setdefault((record.module_id, record.level), []).append(record)
    summaries = []
    for module, level in sorted(grouped, key=lambda item: (item[0], item[1])):
        subset = grouped[(module, level)]
        correct = sum(1 for record in subset if record.is_correct)
        summaries.append(
            LevelSummary(
                module_id=module,
                level=level,
                attempts=len(subset),
                correct=correct,
                accuracy=correct / len(subset),
            )
        )
    return summaries


def recent(records: list[AttemptRecord], limit: int = 100) -> list[AttemptRecord]:
    return list(reversed(records[-limit:]))


def _local_day(moment: datetime) -> date:
    return moment.astimezone().date()
