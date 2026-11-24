"""Contrato y quality gate de los modelos serializados en models/.

Estas pruebas protegen el artefacto que se despliega:
  * se carga con las mismas versiones de librerías con que se entrenó,
  * expone la interfaz que la app espera,
  * mantiene un desempeño mínimo sobre el holdout del notebook 05.
Si fallan tras actualizar dependencias o reentrenar, NO se debe desplegar.
"""

import warnings

import joblib
import numpy as np
import pytest
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.metrics import recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from config import MODEL_PATHS, TARGET

# Mismo split que notebooks/05_entrenamiento_modelo.ipynb: es el único
# subconjunto que ningún modelo vio durante el entrenamiento.
HOLDOUT_SIZE = 0.2
HOLDOUT_SEED = 100

# Umbrales mínimos (holdout, umbral de decisión 0.5). Valores de referencia
# al fijarlos: Recall ~0.76 y ROC-AUC ~0.96 para ambos modelos.
MIN_RECALL = 0.70
MIN_ROC_AUC = 0.93

MODEL_NAMES = list(MODEL_PATHS)


@pytest.fixture(scope="module")
def holdout(dataset):
    X = dataset.drop(columns=TARGET)
    y = dataset[TARGET].astype(int)
    _, X_test, _, y_test = train_test_split(X, y, test_size=HOLDOUT_SIZE, random_state=HOLDOUT_SEED)
    return X_test, y_test


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_model_loads_with_training_library_versions(name):
    with warnings.catch_warnings():
        warnings.simplefilter("error", InconsistentVersionWarning)
        joblib.load(MODEL_PATHS[name])


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_model_is_a_full_pipeline(name, trained_models, dataset):
    model = trained_models[name]

    assert isinstance(model, Pipeline)
    assert "preprocessing" in model.named_steps
    missing = set(model.feature_names_in_) - set(dataset.columns)
    assert not missing, f"el modelo espera columnas que el dataset no tiene: {missing}"


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_predict_proba_contract(name, trained_models, holdout):
    X_test, _ = holdout
    proba = trained_models[name].predict_proba(X_test)

    assert proba.shape == (len(X_test), 2)
    assert np.all((proba >= 0) & (proba <= 1))
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, rtol=1e-6)


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_predictions_are_deterministic(name, trained_models, holdout):
    X_test, _ = holdout
    sample = X_test.head(50)
    model = trained_models[name]

    np.testing.assert_array_equal(model.predict_proba(sample), model.predict_proba(sample))


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_unseen_category_does_not_break_prediction(name, trained_models, holdout):
    """El Predictor en Vivo puede recibir categorías nuevas (p. ej. desde un CSV)."""
    X_test, _ = holdout
    row = X_test.head(1).copy()
    row["cartera"] = row["cartera"].astype(str)
    row.loc[:, "cartera"] = "categoria_nunca_vista"

    proba = trained_models[name].predict_proba(row)

    assert proba.shape == (1, 2)


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_quality_gate_on_holdout(name, trained_models, holdout):
    X_test, y_test = holdout
    y_prob = trained_models[name].predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    recall = recall_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_prob)

    assert recall >= MIN_RECALL, f"{name}: recall {recall:.4f} < {MIN_RECALL}"
    assert roc_auc >= MIN_ROC_AUC, f"{name}: ROC-AUC {roc_auc:.4f} < {MIN_ROC_AUC}"
