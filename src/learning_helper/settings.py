"""Preferências configuráveis do Learning Helper.

As constantes de `config.py` continuam sendo os padrões; a dataclass abaixo
guarda uma cópia validada que fica no SQLite. O módulo não importa Tk nem
Streamlit para poder ser testado e usado pelo CLI.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields, replace
from typing import Any

from learning_helper.config import (
    ACCURACY_WINDOW,
    ADULT_PAUSE_SECONDS,
    BATHROOM_DURATION_SECONDS,
    BATHROOM_INTERVAL_SECONDS,
    FEEDBACK_MS,
    INITIAL_INTERVAL_SECONDS,
    INTERVAL_STEP_SECONDS,
    LEVEL_DOWN_THRESHOLD,
    LEVEL_UP_THRESHOLD,
    MAX_INTERVAL_SECONDS,
    MAX_LEVEL,
    MIN_INTERVAL_SECONDS,
    MODULE_ORDER,
    UNLOCK_THRESHOLD,
    WRONG_ANSWER_WAIT_SECONDS,
)

INTERVAL_FLOOR_SECONDS = 60
INTERVAL_CEILING_SECONDS = 60 * 60
INITIAL_INTERVAL_FLOOR_SECONDS = 60
INITIAL_INTERVAL_CEILING_SECONDS = 10 * 60
STEP_FLOOR_SECONDS = 5
STEP_CEILING_SECONDS = 300
ACCURACY_WINDOW_FLOOR = 3
ACCURACY_WINDOW_CEILING = 50
MAX_LEVEL_FLOOR = 1
MAX_LEVEL_CEILING = MAX_LEVEL
FEEDBACK_FLOOR_MS = 500
FEEDBACK_CEILING_MS = 3000
WRONG_ANSWER_WAIT_FLOOR_SECONDS = 10
WRONG_ANSWER_WAIT_CEILING_SECONDS = 300
ADULT_PAUSE_FLOOR_SECONDS = 60
ADULT_PAUSE_CEILING_SECONDS = 120 * 60
BATHROOM_INTERVAL_FLOOR_SECONDS = 5 * 60
BATHROOM_INTERVAL_CEILING_SECONDS = 4 * 60 * 60
BATHROOM_DURATION_FLOOR_SECONDS = 10
BATHROOM_DURATION_CEILING_SECONDS = 300


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _as_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    initial_interval_seconds: int = INITIAL_INTERVAL_SECONDS
    min_interval_seconds: int = MIN_INTERVAL_SECONDS
    max_interval_seconds: int = MAX_INTERVAL_SECONDS
    interval_step_seconds: int = INTERVAL_STEP_SECONDS
    accuracy_window: int = ACCURACY_WINDOW
    unlock_threshold: float = UNLOCK_THRESHOLD
    level_up_threshold: float = LEVEL_UP_THRESHOLD
    level_down_threshold: float = LEVEL_DOWN_THRESHOLD
    max_level: int = MAX_LEVEL
    feedback_ms: int = FEEDBACK_MS
    wrong_answer_wait_seconds: int = WRONG_ANSWER_WAIT_SECONDS
    adult_pause_seconds: int = ADULT_PAUSE_SECONDS
    bathroom_reminder_enabled: bool = True
    bathroom_interval_seconds: int = BATHROOM_INTERVAL_SECONDS
    bathroom_duration_seconds: int = BATHROOM_DURATION_SECONDS
    enabled_modules: tuple[str, ...] = MODULE_ORDER
    update_check_on_startup: bool = True

    def normalized(self) -> Settings:
        """Aplica limites seguros (defensivo ao ler JSON antigo/adulterado)."""
        minimum = _clamp(
            self.min_interval_seconds,
            INTERVAL_FLOOR_SECONDS,
            INTERVAL_CEILING_SECONDS,
        )
        maximum = _clamp(
            self.max_interval_seconds,
            INTERVAL_FLOOR_SECONDS,
            INTERVAL_CEILING_SECONDS,
        )
        if maximum < minimum:
            maximum = minimum
        initial = _clamp(
            self.initial_interval_seconds,
            max(minimum, INITIAL_INTERVAL_FLOOR_SECONDS),
            min(maximum, INITIAL_INTERVAL_CEILING_SECONDS),
        )
        up = max(0.0, min(1.0, float(self.level_up_threshold)))
        down = max(0.0, min(1.0, float(self.level_down_threshold)))
        if down >= up:
            down = max(0.0, up - 0.1)
        modules = [module for module in MODULE_ORDER if module in set(self.enabled_modules)]
        if not modules:
            modules = list(MODULE_ORDER)
        return replace(
            self,
            initial_interval_seconds=initial,
            min_interval_seconds=minimum,
            max_interval_seconds=maximum,
            interval_step_seconds=_clamp(
                self.interval_step_seconds,
                STEP_FLOOR_SECONDS,
                STEP_CEILING_SECONDS,
            ),
            accuracy_window=_clamp(
                self.accuracy_window,
                ACCURACY_WINDOW_FLOOR,
                ACCURACY_WINDOW_CEILING,
            ),
            unlock_threshold=max(0.0, min(1.0, float(self.unlock_threshold))),
            level_up_threshold=up,
            level_down_threshold=down,
            max_level=_clamp(self.max_level, MAX_LEVEL_FLOOR, MAX_LEVEL_CEILING),
            feedback_ms=_clamp(
                self.feedback_ms,
                FEEDBACK_FLOOR_MS,
                FEEDBACK_CEILING_MS,
            ),
            wrong_answer_wait_seconds=_clamp(
                self.wrong_answer_wait_seconds,
                WRONG_ANSWER_WAIT_FLOOR_SECONDS,
                WRONG_ANSWER_WAIT_CEILING_SECONDS,
            ),
            adult_pause_seconds=_clamp(
                self.adult_pause_seconds,
                ADULT_PAUSE_FLOOR_SECONDS,
                ADULT_PAUSE_CEILING_SECONDS,
            ),
            bathroom_interval_seconds=_clamp(
                self.bathroom_interval_seconds,
                BATHROOM_INTERVAL_FLOOR_SECONDS,
                BATHROOM_INTERVAL_CEILING_SECONDS,
            ),
            bathroom_duration_seconds=_clamp(
                self.bathroom_duration_seconds,
                BATHROOM_DURATION_FLOOR_SECONDS,
                BATHROOM_DURATION_CEILING_SECONDS,
            ),
            enabled_modules=tuple(modules),
        )

    def validate(self) -> list[str]:
        """Mensagens de erro para a tela de configuração (vazio = ok)."""
        errors: list[str] = []
        minimum = self.min_interval_seconds
        maximum = self.max_interval_seconds
        if not INTERVAL_FLOOR_SECONDS <= minimum <= INTERVAL_CEILING_SECONDS:
            errors.append(
                f"Intervalo mínimo deve ficar entre {INTERVAL_FLOOR_SECONDS // 60} "
                f"e {INTERVAL_CEILING_SECONDS // 60} minutos."
            )
        if not INTERVAL_FLOOR_SECONDS <= maximum <= INTERVAL_CEILING_SECONDS:
            errors.append(
                f"Intervalo máximo deve ficar entre {INTERVAL_FLOOR_SECONDS // 60} "
                f"e {INTERVAL_CEILING_SECONDS // 60} minutos."
            )
        if maximum < minimum:
            errors.append("O intervalo máximo não pode ser menor que o mínimo.")
        elif not minimum <= self.initial_interval_seconds <= maximum:
            errors.append("O intervalo inicial deve ficar entre o mínimo e o máximo.")
        if not STEP_FLOOR_SECONDS <= self.interval_step_seconds <= STEP_CEILING_SECONDS:
            errors.append(
                f"O passo por resposta deve ficar entre {STEP_FLOOR_SECONDS} e "
                f"{STEP_CEILING_SECONDS} segundos."
            )
        if not ACCURACY_WINDOW_FLOOR <= self.accuracy_window <= ACCURACY_WINDOW_CEILING:
            errors.append(
                f"A janela de precisão deve ficar entre {ACCURACY_WINDOW_FLOOR} e "
                f"{ACCURACY_WINDOW_CEILING} tentativas."
            )
        for label, value in (
            ("desbloqueio", self.unlock_threshold),
            ("subir de nível", self.level_up_threshold),
            ("descer de nível", self.level_down_threshold),
        ):
            if not 0.0 <= value <= 1.0:
                errors.append(f"O limite de {label} deve ficar entre 0% e 100%.")
        if self.level_down_threshold >= self.level_up_threshold:
            errors.append("O limite para descer de nível deve ser menor que o de subir.")
        if not MAX_LEVEL_FLOOR <= self.max_level <= MAX_LEVEL_CEILING:
            errors.append(
                f"O nível máximo deve ficar entre {MAX_LEVEL_FLOOR} e {MAX_LEVEL_CEILING}."
            )
        if not FEEDBACK_FLOOR_MS <= self.feedback_ms <= FEEDBACK_CEILING_MS:
            errors.append(
                f"O feedback deve durar entre {FEEDBACK_FLOOR_MS / 1000:.1f} e "
                f"{FEEDBACK_CEILING_MS / 1000:.1f} segundos."
            )
        if not (
            WRONG_ANSWER_WAIT_FLOOR_SECONDS
            <= self.wrong_answer_wait_seconds
            <= WRONG_ANSWER_WAIT_CEILING_SECONDS
        ):
            errors.append(
                "A espera após resposta errada deve ficar entre "
                f"{WRONG_ANSWER_WAIT_FLOOR_SECONDS} e "
                f"{WRONG_ANSWER_WAIT_CEILING_SECONDS} segundos."
            )
        if not (
            ADULT_PAUSE_FLOOR_SECONDS
            <= self.adult_pause_seconds
            <= ADULT_PAUSE_CEILING_SECONDS
        ):
            errors.append(
                f"A pausa do adulto deve ficar entre {ADULT_PAUSE_FLOOR_SECONDS // 60} "
                f"e {ADULT_PAUSE_CEILING_SECONDS // 60} minutos."
            )
        if not (
            BATHROOM_INTERVAL_FLOOR_SECONDS
            <= self.bathroom_interval_seconds
            <= BATHROOM_INTERVAL_CEILING_SECONDS
        ):
            errors.append(
                "O intervalo do lembrete de banheiro deve ficar entre "
                f"{BATHROOM_INTERVAL_FLOOR_SECONDS // 60} minutos e "
                f"{BATHROOM_INTERVAL_CEILING_SECONDS // 3600} horas."
            )
        if not (
            BATHROOM_DURATION_FLOOR_SECONDS
            <= self.bathroom_duration_seconds
            <= BATHROOM_DURATION_CEILING_SECONDS
        ):
            errors.append(
                "O lembrete de banheiro deve durar entre "
                f"{BATHROOM_DURATION_FLOOR_SECONDS} e "
                f"{BATHROOM_DURATION_CEILING_SECONDS} segundos."
            )
        modules = list(self.enabled_modules)
        if not modules:
            errors.append("Mantenha pelo menos um módulo ativo.")
        elif len(set(modules)) != len(modules):
            errors.append("Módulos ativos não podem se repetir.")
        elif any(module not in MODULE_ORDER for module in modules):
            errors.append("Módulo ativo desconhecido.")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Any) -> Settings:
        defaults = cls()
        if not isinstance(data, dict):
            return defaults.normalized()
        values: dict[str, Any] = {}
        for item in fields(cls):
            if item.name not in data:
                continue
            raw = data[item.name]
            current = getattr(defaults, item.name)
            if item.name == "enabled_modules":
                if isinstance(raw, (list, tuple)):
                    values[item.name] = tuple(
                        str(module) for module in raw if isinstance(module, str)
                    )
                continue
            if isinstance(current, bool):
                values[item.name] = bool(raw)
            elif isinstance(current, float):
                values[item.name] = _as_float(raw, current)
            else:
                values[item.name] = _as_int(raw, current)
        return replace(defaults, **values).normalized()

    @classmethod
    def from_json(cls, raw: str | None) -> Settings:
        if not raw:
            return cls()
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return cls()
        return cls.from_dict(data)
