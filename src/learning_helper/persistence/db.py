from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from learning_helper.adaptive.models import Attempt, Profile
from learning_helper.config import INITIAL_INTERVAL_SECONDS, MODULE_ORDER
from learning_helper.settings import Settings

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def data_dir(
    platform: str | None = None, env: Mapping[str, str] | None = None
) -> Path:
    """Diretório de dados do usuário, por plataforma."""
    system = platform or sys.platform
    environment = os.environ if env is None else env
    if system == "win32":
        base = environment.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = environment.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "learning_helper"


def default_db_path() -> Path:
    return data_dir() / "learning_helper.db"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dumps_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime(ISO_FORMAT)


def _loads_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, ISO_FORMAT).replace(tzinfo=timezone.utc)


def schema_sql() -> str:
    schema_path = Path(__file__).with_name("schema.sql")
    return schema_path.read_text(encoding="utf-8")


class Store:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else default_db_path()
        self._db_existed = (
            self.db_path.exists() and self.db_path.stat().st_size > 0
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._init_schema()
        self._ensure_profile()
        self._ensure_settings()
        self._migrate_unlocked_modules()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(schema_sql())
        self._migrate_profile_columns()
        self._conn.commit()

    def _migrate_profile_columns(self) -> None:
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(profile)").fetchall()
        }
        if "interval_seconds" not in columns:
            # Bancos criados antes do intervalo adaptativo: a linha existente
            # assume o intervalo inicial (3 minutos).
            self._conn.execute(
                "ALTER TABLE profile ADD COLUMN interval_seconds "
                f"INTEGER NOT NULL DEFAULT {int(INITIAL_INTERVAL_SECONDS)}"
            )
        if "last_bathroom_reminder_at" not in columns:
            self._conn.execute(
                "ALTER TABLE profile ADD COLUMN last_bathroom_reminder_at TEXT"
            )

    def _ensure_profile(self) -> None:
        row = self._conn.execute("SELECT id FROM profile WHERE id = 1").fetchone()
        if row is None:
            profile = Profile.default()
            self.save_profile(profile)

    def _ensure_settings(self) -> None:
        row = self._conn.execute("SELECT id FROM settings WHERE id = 1").fetchone()
        if row is not None:
            return
        settings = Settings()
        columns = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(profile)").fetchall()
        }
        if "bathroom_reminder_enabled" in columns:
            # Bancos até a 0.3.x guardavam a preferência no profile; ela passa
            # a viver nas settings (a coluna antiga fica para trás, sem uso).
            legacy = self._conn.execute(
                "SELECT bathroom_reminder_enabled FROM profile WHERE id = 1"
            ).fetchone()
            if legacy is not None:
                settings = replace(
                    settings,
                    bathroom_reminder_enabled=bool(legacy["bathroom_reminder_enabled"]),
                )
        self._conn.execute(
            """
            INSERT INTO settings (id, onboarding_completed, values_json, updated_at)
            VALUES (1, ?, ?, ?)
            """,
            (
                int(self._db_existed),
                settings.to_json(),
                _dumps_dt(_utc_now()),
            ),
        )
        self._conn.commit()

    def _migrate_unlocked_modules(self) -> None:
        """Perfis antigos recebem `problems` logo depois de `math`."""
        profile = self.get_profile()
        unlocked = list(profile.unlocked_modules)
        if "math" in unlocked and "problems" not in unlocked:
            unlocked.append("problems")

        ordered = [module for module in MODULE_ORDER if module in unlocked]
        ordered += [module for module in unlocked if module not in MODULE_ORDER]
        if ordered != profile.unlocked_modules:
            profile.unlocked_modules = ordered
            self.save_profile(profile)

    def get_profile(self) -> Profile:
        row = self._conn.execute(
            """
            SELECT unlocked_modules_json, levels_json, last_interrupt_at,
                   adult_pause_until, interval_seconds, last_bathroom_reminder_at
            FROM profile WHERE id = 1
            """
        ).fetchone()
        unlocked = json.loads(row["unlocked_modules_json"])
        levels = json.loads(row["levels_json"])
        for module in MODULE_ORDER:
            levels.setdefault(module, 1)
        return Profile(
            unlocked_modules=unlocked,
            levels=levels,
            last_interrupt_at=_loads_dt(row["last_interrupt_at"]),
            adult_pause_until=_loads_dt(row["adult_pause_until"]),
            interval_seconds=int(row["interval_seconds"]),
            last_bathroom_reminder_at=_loads_dt(row["last_bathroom_reminder_at"]),
        )

    def save_profile(self, profile: Profile) -> None:
        self._conn.execute(
            """
            INSERT INTO profile (id, unlocked_modules_json, levels_json, last_interrupt_at, adult_pause_until, interval_seconds, last_bathroom_reminder_at)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                unlocked_modules_json = excluded.unlocked_modules_json,
                levels_json = excluded.levels_json,
                last_interrupt_at = excluded.last_interrupt_at,
                adult_pause_until = excluded.adult_pause_until,
                interval_seconds = excluded.interval_seconds,
                last_bathroom_reminder_at = excluded.last_bathroom_reminder_at
            """,
            (
                json.dumps(profile.unlocked_modules),
                json.dumps(profile.levels),
                _dumps_dt(profile.last_interrupt_at),
                _dumps_dt(profile.adult_pause_until),
                profile.interval_seconds,
                _dumps_dt(profile.last_bathroom_reminder_at),
            ),
        )
        self._conn.commit()

    def get_settings(self) -> Settings:
        row = self._conn.execute(
            "SELECT values_json FROM settings WHERE id = 1"
        ).fetchone()
        return Settings.from_json(row["values_json"] if row else None)

    def save_settings(self, settings: Settings) -> Settings:
        errors = settings.validate()
        if errors:
            raise ValueError(" ".join(errors))
        normalized = settings.normalized()
        self._conn.execute(
            "UPDATE settings SET values_json = ?, updated_at = ? WHERE id = 1",
            (normalized.to_json(), _dumps_dt(_utc_now())),
        )
        self._conn.commit()
        return normalized

    def onboarding_completed(self) -> bool:
        row = self._conn.execute(
            "SELECT onboarding_completed FROM settings WHERE id = 1"
        ).fetchone()
        return bool(row["onboarding_completed"]) if row else False

    def complete_onboarding(self) -> None:
        self._conn.execute(
            "UPDATE settings SET onboarding_completed = 1, updated_at = ? WHERE id = 1",
            (_dumps_dt(_utc_now()),),
        )
        self._conn.commit()

    def insert_attempt(
        self,
        *,
        module_id: str,
        level: int,
        prompt: str,
        choices: list[str],
        correct_answer: str,
        given_answer: str,
        is_correct: bool,
        spec_json: dict | None = None,
        created_at: datetime | None = None,
    ) -> Attempt:
        created = created_at or _utc_now()
        cursor = self._conn.execute(
            """
            INSERT INTO attempts (
                created_at, module_id, level, prompt, choices_json,
                correct_answer, given_answer, is_correct, spec_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _dumps_dt(created),
                module_id,
                level,
                prompt,
                json.dumps(choices),
                correct_answer,
                given_answer,
                int(is_correct),
                json.dumps(spec_json) if spec_json is not None else None,
            ),
        )
        self._conn.commit()
        return Attempt(
            id=cursor.lastrowid,
            created_at=created,
            module_id=module_id,
            level=level,
            prompt=prompt,
            choices=choices,
            correct_answer=correct_answer,
            given_answer=given_answer,
            is_correct=is_correct,
            spec_json=spec_json,
        )

    def recent_attempts(self, module_id: str, limit: int) -> list[Attempt]:
        rows = self._conn.execute(
            """
            SELECT * FROM attempts
            WHERE module_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (module_id, limit),
        ).fetchall()
        return [self._row_to_attempt(row) for row in reversed(rows)]

    def count_attempts(self, module_id: str | None = None) -> int:
        if module_id is None:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM attempts").fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM attempts WHERE module_id = ?",
                (module_id,),
            ).fetchone()
        return int(row["n"])

    def _row_to_attempt(self, row: sqlite3.Row) -> Attempt:
        spec = json.loads(row["spec_json"]) if row["spec_json"] else None
        return Attempt(
            id=row["id"],
            created_at=_loads_dt(row["created_at"]) or _utc_now(),
            module_id=row["module_id"],
            level=row["level"],
            prompt=row["prompt"],
            choices=json.loads(row["choices_json"]),
            correct_answer=row["correct_answer"],
            given_answer=row["given_answer"],
            is_correct=bool(row["is_correct"]),
            spec_json=spec,
        )
