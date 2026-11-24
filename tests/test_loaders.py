"""Pruebas de carga y preprocesamiento de datos y modelos (utils/loaders.py)."""

import io

import pandas as pd
import pytest

from config import DROP_COLS, MODEL_PATHS, TARGET
from utils import loaders


def test_default_dataset_is_clean():
    raw, clean = loaders.load_and_preprocess(None, use_default=True)

    assert len(raw) > 0
    assert TARGET in clean.columns
    assert clean[TARGET].dtype.kind == "i"
    assert set(clean[TARGET].unique()) <= {0, 1}
    assert not clean.isna().any().any()
    assert clean.select_dtypes(include=["category"]).empty
    assert not set(DROP_COLS) & set(clean.columns)


def test_uploaded_csv_is_preprocessed():
    csv = pd.DataFrame(
        {
            "Unnamed: 0": [0, 1, 2],
            "n.credito": [101, 102, 103],
            "edad": [30, None, 45],
            "cartera": ["vivienda", "vivienda", "consumo_con_libranza"],
            TARGET: [True, False, False],
        }
    ).to_csv(index=False)

    raw, clean = loaders.load_and_preprocess(io.BytesIO(csv.encode()), use_default=False)

    assert len(raw) == 3
    assert len(clean) == 2, "las filas con nulos deben descartarse"
    assert list(clean.columns) == ["edad", "cartera", TARGET]
    assert clean[TARGET].tolist() == [1, 0]


def test_load_models_returns_every_configured_model():
    models = loaders.load_models()

    assert set(models) == set(MODEL_PATHS)
    assert all(hasattr(m, "predict_proba") for m in models.values())


class _AppStopped(Exception):
    pass


def test_load_models_stops_app_when_a_file_is_missing(monkeypatch):
    errors = []
    monkeypatch.setattr(loaders, "MODEL_PATHS", {"Fantasma": "models/no_existe.joblib"})
    monkeypatch.setattr(loaders.st, "error", errors.append)
    monkeypatch.setattr(loaders.st, "stop", lambda: (_ for _ in ()).throw(_AppStopped()))
    loaders.load_models.clear()

    try:
        with pytest.raises(_AppStopped):
            loaders.load_models()
    finally:
        loaders.load_models.clear()

    assert "models/no_existe.joblib" in errors[0]
