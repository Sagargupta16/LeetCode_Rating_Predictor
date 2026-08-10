"""Framework-free model loading.

The trained network is a small feed-forward stack of Dense layers, so serving a
prediction is a handful of matrix multiplies. Loading the exported artifacts
(``models/weights.npz`` + ``models/scaler.json``) keeps TensorFlow, Keras,
scikit-learn and joblib out of the runtime entirely.

Regenerate the artifacts with ``python scripts/export_model.py`` after
retraining.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_SUPPORTED_ACTIVATIONS = {"relu", "linear"}


class DenseNetwork:
    """Feed-forward network evaluated with numpy.

    Mirrors the Keras inference path: weights are float32 and inputs are cast to
    float32 before the first matmul. Dropout layers are omitted at export time
    because they are the identity outside training.

    Exposes ``input_shape`` and ``predict`` so it is interchangeable with a
    Keras model for the prediction service.
    """

    def __init__(
        self,
        weights: list[tuple[np.ndarray, np.ndarray]],
        activations: list[str],
        input_dim: int,
    ):
        if len(weights) != len(activations):
            raise ValueError("weights and activations must have the same length")
        if not weights:
            raise ValueError("model has no layers")
        self._weights = weights
        self._activations = activations
        self.input_shape = (None, input_dim)

    def predict(self, x: np.ndarray) -> np.ndarray:
        """Run a forward pass."""
        activations = np.asarray(x, dtype=np.float32)
        if activations.ndim != 2:
            raise ValueError(f"expected a 2D input, got shape {activations.shape}")
        expected = self.input_shape[1]
        if activations.shape[1] != expected:
            raise ValueError(
                f"expected {expected} features, got {activations.shape[1]}"
            )

        for (kernel, bias), activation in zip(
            self._weights, self._activations, strict=True
        ):
            activations = activations @ kernel + bias
            if activation == "relu":
                activations = np.maximum(activations, 0, dtype=np.float32)
        return activations


class MinMaxScaler:
    """Applies ``x * scale + min``, matching ``sklearn`` MinMaxScaler.transform."""

    def __init__(self, scale: np.ndarray, minimum: np.ndarray):
        if scale.shape != minimum.shape:
            raise ValueError("scale and min must have the same shape")
        self._scale = scale
        self._min = minimum
        self.n_features_in_ = int(scale.shape[0])

    def transform(self, x: np.ndarray) -> np.ndarray:
        values = np.asarray(x, dtype=np.float64)
        if values.ndim != 2:
            raise ValueError(f"expected a 2D input, got shape {values.shape}")
        if values.shape[1] != self.n_features_in_:
            raise ValueError(
                f"expected {self.n_features_in_} features, got {values.shape[1]}"
            )
        return values * self._scale + self._min


def load_model(weights_path: str | Path) -> DenseNetwork:
    """Load a network exported by ``scripts/export_model.py``."""
    path = Path(weights_path)
    with np.load(path) as archive:
        meta = json.loads(str(archive["meta"]))
        layer_count = int(meta["layers"])
        activations = list(meta["activations"])

        unsupported = set(activations) - _SUPPORTED_ACTIVATIONS
        if unsupported:
            raise ValueError(
                f"unsupported activations in {path}: {sorted(unsupported)}"
            )

        weights = [
            (
                np.asarray(archive[f"w{i}"], dtype=np.float32),
                np.asarray(archive[f"b{i}"], dtype=np.float32),
            )
            for i in range(layer_count)
        ]

    model = DenseNetwork(weights, activations, int(meta["input_dim"]))
    logger.info(
        "loaded model from %s (%d layers, input_dim=%d)",
        path,
        layer_count,
        meta["input_dim"],
    )
    return model


def load_scaler(scaler_path: str | Path) -> MinMaxScaler:
    """Load a scaler exported by ``scripts/export_model.py``."""
    path = Path(scaler_path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    if payload.get("type") != "MinMaxScaler":
        raise ValueError(f"unsupported scaler type {payload.get('type')!r} in {path}")

    scaler = MinMaxScaler(
        np.asarray(payload["scale"], dtype=np.float64),
        np.asarray(payload["min"], dtype=np.float64),
    )
    logger.info("loaded scaler from %s (%d features)", path, scaler.n_features_in_)
    return scaler
