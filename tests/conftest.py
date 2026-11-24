"""Fixtures compartidas por toda la suite."""

from pathlib import Path

import joblib
import pandas as pd
import pytest

from config import DEFAULT_DATA_PATH, MODEL_PATHS

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _run_from_project_root(monkeypatch):
    """La app y config.py usan rutas relativas a la raíz del repositorio."""
    monkeypatch.chdir(ROOT)


@pytest.fixture(scope="session")
def dataset() -> pd.DataFrame:
    """Dataset procesado tal cual se usó para entrenar (notebook 05)."""
    return pd.read_parquet(ROOT / DEFAULT_DATA_PATH)


@pytest.fixture(scope="session")
def trained_models() -> dict:
    return {name: joblib.load(ROOT / path) for name, path in MODEL_PATHS.items()}
