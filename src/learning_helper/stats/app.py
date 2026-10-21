"""Interface Streamlit das estatísticas (somente leitura)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from learning_helper.config import MODULE_LABELS, MODULE_ORDER
from learning_helper.persistence.db import default_db_path
from learning_helper.stats import data

PERIODS = {"7 dias": 7, "30 dias": 30, "90 dias": 90, "Tudo": None}


def _db_path() -> Path:
    configured = os.environ.get("LEARNING_HELPER_DB")
    return Path(configured) if configured else default_db_path()


@st.cache_data(ttl=15, show_spinner=False)
def _load_attempts(
    db_path: str,
    days: int | None,
    modules: tuple[str, ...],
) -> list[data.AttemptRecord]:
    since = (
        None
        if days is None
        else datetime.now(timezone.utc) - timedelta(days=days)
    )
    return data.load_attempts(
        Path(db_path),
        since=since,
        module_ids=modules or None,
    )


@st.cache_data(ttl=15, show_spinner=False)
def _load_profile(db_path: str) -> data.ProfileSummary | None:
    return data.load_profile(Path(db_path))


def _module_label(module: str) -> str:
    return MODULE_LABELS.get(module, module)


def _local_time(moment: datetime) -> str:
    return moment.astimezone().strftime("%d/%m/%Y %H:%M")


def _accuracy(value: float) -> str:
    return f"{value * 100:.0f}%"


def _status(module: str, profile: data.ProfileSummary | None) -> str:
    if profile is None:
        return "—"
    if module not in profile.enabled_modules:
        return "Desativado"
    if module in profile.unlocked:
        return "Liberado"
    return "Bloqueado"


def main() -> None:
    st.set_page_config(
        page_title="Learning Helper — Estatísticas",
        page_icon="📊",
        layout="wide",
    )
    db_path = _db_path()

    st.title("📊 Learning Helper — Estatísticas")
    st.caption(
        "Somente leitura: estes números não alteram o banco, os níveis ou os "
        "desafios da criança."
    )

    if not db_path.exists():
        st.info(
            "Ainda não há dados. Abra o Learning Helper e responda a um desafio "
            "para as estatísticas aparecerem aqui."
        )
        st.caption(f"Banco esperado em: {db_path}")
        st.stop()

    with st.sidebar:
        st.header("Filtros")
        period_label = st.selectbox("Período", list(PERIODS), index=1)
        selected_modules = st.multiselect(
            "Módulos",
            options=list(MODULE_ORDER),
            default=list(MODULE_ORDER),
            format_func=_module_label,
        )
        if st.button("Atualizar agora"):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.caption(f"Banco: {db_path}")

    if not selected_modules:
        st.info("Selecione pelo menos um módulo na barra lateral.")
        st.stop()

    try:
        records = _load_attempts(
            str(db_path), PERIODS[period_label], tuple(selected_modules)
        )
        profile = _load_profile(str(db_path))
    except data.StatsDataError as exc:
        st.error(str(exc))
        st.stop()

    totals = data.kpis(records)
    columns = st.columns(4)
    columns[0].metric("Tentativas", totals.attempts)
    columns[1].metric("Acertos", totals.correct)
    columns[2].metric("Precisão", _accuracy(totals.accuracy))
    columns[3].metric("Dias ativos", totals.active_days)

    if not records:
        st.info(
            "Ainda não há tentativas no período selecionado. Experimente "
            "escolher “Tudo”."
        )
        st.stop()

    evolution, modules, attempts = st.tabs(
        ["Evolução", "Módulos e níveis", "Tentativas recentes"]
    )

    with evolution:
        daily = data.by_day(records)
        frame = pd.DataFrame(
            {
                "Dia": pd.to_datetime([item.day for item in daily]),
                "Tentativas": [item.attempts for item in daily],
                "Precisão (%)": [round(item.accuracy * 100, 1) for item in daily],
            }
        ).set_index("Dia")
        st.subheader("Tentativas por dia")
        st.bar_chart(frame["Tentativas"])
        st.subheader("Precisão por dia")
        st.line_chart(frame["Precisão (%)"])
        st.caption(
            "A precisão é calculada sobre as tentativas do dia; dias sem "
            "tentativas não aparecem no gráfico."
        )

    with modules:
        summaries = {item.module_id: item for item in data.by_module(records)}
        rows = []
        for module in MODULE_ORDER:
            item = summaries.get(module)
            rows.append(
                {
                    "Módulo": _module_label(module),
                    "Tentativas": item.attempts if item else 0,
                    "Precisão (%)": (
                        round(item.accuracy * 100, 1) if item else None
                    ),
                    "Nível atual": (
                        profile.levels.get(module, 1) if profile else "—"
                    ),
                    "Status": _status(module, profile),
                }
            )
        st.subheader("Resumo por módulo")
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            use_container_width=True,
        )

        levels = data.by_level(records)
        if levels:
            st.subheader("Precisão por nível")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Módulo": _module_label(item.module_id),
                            "Nível": item.level,
                            "Tentativas": item.attempts,
                            "Acertos": item.correct,
                            "Precisão (%)": round(item.accuracy * 100, 1),
                        }
                        for item in levels
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )

    with attempts:
        st.subheader("Últimas 100 tentativas")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Data": _local_time(record.created_at),
                        "Módulo": _module_label(record.module_id),
                        "Nível": record.level,
                        "Enunciado": record.prompt,
                        "Resposta": record.given_answer,
                        "Gabarito": record.correct_answer,
                        "Resultado": "Certo" if record.is_correct else "Errado",
                    }
                    for record in data.recent(records, 100)
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )


main()
