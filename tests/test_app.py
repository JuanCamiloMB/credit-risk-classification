"""Smoke tests de la app Streamlit completa (sin navegador) con AppTest."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

pytestmark = pytest.mark.slow

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
TIMEOUT_S = 180


@pytest.fixture
def app() -> AppTest:
    return AppTest.from_file(str(APP_PATH), default_timeout=TIMEOUT_S).run()


def test_app_renders_all_tabs_without_errors(app):
    assert not app.exception, app.exception
    assert not app.error
    assert [t.label for t in app.tabs] == [
        "📊 Resumen del Dataset",
        "🔍 Análisis Exploratorio",
        "🤖 Resultados de los Modelos",
        "🎯 Predictor en Vivo",
    ]


def test_changing_threshold_reruns_cleanly(app):
    app.sidebar.slider[1].set_value(0.3).run()

    assert not app.exception, app.exception


def test_live_predictor_returns_a_prediction(app):
    app.button[0].click().run()

    assert not app.exception, app.exception
    labels = [m.label for m in app.metric]
    assert "⚖️ Ensemble (promedio)" in labels


def test_upload_mode_waits_for_a_file(app):
    app.sidebar.radio[0].set_value("⬆️ Subir un archivo CSV").run()

    assert not app.exception, app.exception
    assert any("Sube un archivo CSV" in i.value for i in app.info)
    assert not app.tabs, "sin archivo la app no debe renderizar las pestañas"
