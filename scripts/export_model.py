"""Export the trained Keras model and scaler into framework-free artifacts.

The served model is a plain feed-forward network, so inference needs nothing
beyond a few matrix multiplies. This script converts:

    model.keras   -> models/weights.npz   (Dense kernels/biases + activations)
    scaler.save   -> models/scaler.json   (MinMaxScaler scale_/min_ vectors)

so the API can run without TensorFlow, Keras, scikit-learn or joblib.

Run it after retraining, with the ML extras installed:

    pip install -r requirements-ml.txt
    python scripts/export_model.py
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SUPPORTED_ACTIVATIONS = {"relu", "linear"}
REPO_ROOT = Path(__file__).resolve().parent.parent

# Output locations are fixed rather than CLI arguments: the API reads exactly
# these two paths, so there is nothing to configure and no caller-supplied path
# ever reaches mkdir or a write.
WEIGHTS_OUT = REPO_ROOT / "models" / "weights.npz"
SCALER_OUT = REPO_ROOT / "models" / "scaler.json"


def export_weights(model_path: Path) -> None:
    """Flatten the model's Dense layers into a single .npz archive."""
    import tensorflow as tf

    model = tf.keras.models.load_model(model_path)

    arrays: dict[str, np.ndarray] = {}
    activations: list[str] = []
    index = 0

    for layer in model.layers:
        class_name = type(layer).__name__
        if class_name == "Dropout":
            # Dropout is identity at inference time.
            continue
        if class_name == "InputLayer":
            continue
        if class_name != "Dense":
            raise ValueError(
                f"Unsupported layer {class_name!r}. Only Dense/Dropout/InputLayer "
                "can be exported; update this script if the architecture changed."
            )

        activation = getattr(layer.activation, "__name__", "linear")
        if activation not in SUPPORTED_ACTIVATIONS:
            raise ValueError(
                f"Unsupported activation {activation!r} on layer {layer.name!r}."
            )

        kernel, bias = layer.get_weights()
        arrays[f"w{index}"] = np.asarray(kernel, dtype=np.float32)
        arrays[f"b{index}"] = np.asarray(bias, dtype=np.float32)
        activations.append(activation)
        index += 1

    if not arrays:
        raise ValueError("No Dense layers found in the model")

    input_dim = int(arrays["w0"].shape[0])
    meta = {"activations": activations, "input_dim": input_dim, "layers": index}

    WEIGHTS_OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez(WEIGHTS_OUT, meta=json.dumps(meta), **arrays)
    logger.info(
        "wrote %s (%d Dense layers, input_dim=%d, activations=%s)",
        WEIGHTS_OUT,
        index,
        input_dim,
        activations,
    )


def export_scaler(scaler_path: Path) -> None:
    """Reduce the pickled MinMaxScaler to its two transform vectors.

    ``MinMaxScaler.transform`` is ``x * scale_ + min_``, so nothing else is
    needed and the pickle never has to be loaded at runtime.
    """
    import joblib

    scaler = joblib.load(scaler_path)

    if not hasattr(scaler, "scale_") or not hasattr(scaler, "min_"):
        raise TypeError(
            f"Expected a MinMaxScaler-like object, got {type(scaler).__name__}"
        )
    if getattr(scaler, "clip", False):
        raise ValueError("Scalers with clip=True are not supported by the exporter")

    payload = {
        "type": "MinMaxScaler",
        "n_features_in": int(scaler.n_features_in_),
        "scale": np.asarray(scaler.scale_, dtype=np.float64).tolist(),
        "min": np.asarray(scaler.min_, dtype=np.float64).tolist(),
    }

    SCALER_OUT.parent.mkdir(parents=True, exist_ok=True)
    SCALER_OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logger.info("wrote %s (%d features)", SCALER_OUT, payload["n_features_in"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="model.keras", type=Path)
    parser.add_argument("--scaler", default="scaler.save", type=Path)
    args = parser.parse_args()

    export_weights(args.model)
    export_scaler(args.scaler)


if __name__ == "__main__":
    main()
