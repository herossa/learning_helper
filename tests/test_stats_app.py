from pathlib import Path

from streamlit.testing.v1 import AppTest

from learning_helper.persistence.db import Store

APP = Path(__file__).resolve().parents[1] / "src" / "learning_helper" / "stats" / "app.py"


def _app(tmp_path, monkeypatch) -> tuple[AppTest, Path]:
    db_path = tmp_path / "learning_helper.db"
    monkeypatch.setenv("LEARNING_HELPER_DB", str(db_path))
    app = AppTest.from_file(str(APP), default_timeout=30)
    return app, db_path


def test_dashboard_renders_metrics(tmp_path, monkeypatch) -> None:
    app, db_path = _app(tmp_path, monkeypatch)
    store = Store(db_path)
    try:
        for index in range(3):
            store.insert_attempt(
                module_id="colors",
                level=1,
                prompt=f"Desafio {index}",
                choices=["a", "b"],
                correct_answer="a",
                given_answer="a" if index < 2 else "b",
                is_correct=index < 2,
            )
    finally:
        store.close()

    app.run()
    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Tentativas"] == "3"
    assert metrics["Acertos"] == "2"
    assert metrics["Precisão"] == "67%"


def test_dashboard_shows_empty_state(tmp_path, monkeypatch) -> None:
    app, db_path = _app(tmp_path, monkeypatch)
    Store(db_path).close()

    app.run()
    assert not app.exception
    assert app.info


def test_dashboard_shows_missing_database_message(tmp_path, monkeypatch) -> None:
    app, _ = _app(tmp_path, monkeypatch)

    app.run()
    assert not app.exception
    assert app.info
