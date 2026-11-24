"""Pruebas unitarias de utils/metrics.py."""

import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from utils.metrics import (
    clf_metrics,
    compute_probs,
    evaluate_all,
    get_pipeline_input_features,
)

EXPECTED_KEYS = {"Exactitud", "Recall", "F1", "ROC-AUC", "Prec. Prom."}


def test_clf_metrics_perfect_classifier():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.8, 0.9])
    metrics = clf_metrics(y_true, (y_prob >= 0.5).astype(int), y_prob)

    assert set(metrics) == EXPECTED_KEYS
    assert all(value == 1.0 for value in metrics.values())


def test_clf_metrics_recall_is_on_default_class():
    # 2 defaults reales, el modelo detecta 1 -> recall = 0.5
    y_true = np.array([1, 1, 0, 0])
    y_pred = np.array([1, 0, 0, 0])
    y_prob = np.array([0.9, 0.4, 0.2, 0.1])

    assert clf_metrics(y_true, y_pred, y_prob)["Recall"] == 0.5


def test_clf_metrics_without_positive_predictions_does_not_crash():
    y_true = np.array([1, 0, 1, 0])
    y_pred = np.zeros(4, dtype=int)
    y_prob = np.array([0.4, 0.1, 0.3, 0.2])

    metrics = clf_metrics(y_true, y_pred, y_prob)

    assert metrics["Recall"] == 0.0
    assert metrics["F1"] == 0.0


@pytest.mark.parametrize(
    ("threshold", "expected"),
    [(0.5, [0, 1, 1]), (0.7, [0, 0, 1]), (0.1, [1, 1, 1])],
)
def test_evaluate_all_applies_threshold(threshold, expected):
    y_test = np.array([0, 1, 1])
    probs = {"modelo": np.array([0.2, 0.6, 0.8])}

    results = evaluate_all(probs, y_test, threshold)

    assert results["modelo"]["y_pred"].tolist() == expected
    assert set(results["modelo"]["metrics"]) == EXPECTED_KEYS


class _ConstantModel:
    def __init__(self, p: float):
        self.p = p

    def predict_proba(self, X):
        return np.column_stack([np.full(len(X), 1 - self.p), np.full(len(X), self.p)])


def test_compute_probs_returns_positive_class_probability():
    X = pd.DataFrame({"a": [1, 2, 3]})
    models = {"bajo": _ConstantModel(0.1), "alto": _ConstantModel(0.9)}

    probs = compute_probs(models, X, ("bajo", "alto"))

    assert probs["bajo"].tolist() == pytest.approx([0.1] * 3)
    assert probs["alto"].tolist() == pytest.approx([0.9] * 3)


def _fitted_pipeline() -> Pipeline:
    X = pd.DataFrame(
        {"edad": [30, 40, 50, 60], "plazo": [12, 24, 36, 48], "cartera": ["a", "b", "a", "b"]}
    )
    y = [0, 1, 0, 1]
    pre = ColumnTransformer(
        [
            ("numericas", StandardScaler(), ["edad", "plazo"]),
            ("categoricas", OneHotEncoder(handle_unknown="ignore"), ["cartera"]),
        ]
    )
    return Pipeline([("preprocessing", pre), ("classifier", LogisticRegression())]).fit(X, y)


def test_get_pipeline_input_features_from_column_transformer():
    assert get_pipeline_input_features(_fitted_pipeline()) == ["edad", "plazo", "cartera"]


def test_get_pipeline_input_features_bare_estimator_returns_none():
    assert get_pipeline_input_features(LogisticRegression()) is None


def test_get_pipeline_input_features_without_column_transformer_returns_none():
    pipe = Pipeline([("scaler", StandardScaler()), ("classifier", LogisticRegression())])
    assert get_pipeline_input_features(pipe) is None
