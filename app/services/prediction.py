"""Model prediction service."""

import logging
import math

import numpy as np
from fastapi import HTTPException

from app.config import MAX_RATING_CHANGE

logger = logging.getLogger(__name__)


def make_prediction(model, scaler, input_data: np.ndarray) -> float:
    """Predict a rating change from a (1, num_features) feature array.

    The scaler normalises the features and the model produces a scalar. Works
    with both the exported Dense network and legacy LSTM-shaped models.
    """
    try:
        if model is None or scaler is None:
            raise RuntimeError("Model or scaler not loaded")

        input_scaled = scaler.transform(input_data)

        # If the model expects 3D input (legacy LSTM), reshape accordingly
        expected = model.input_shape
        if len(expected) == 3:
            input_scaled = input_scaled.reshape(
                (input_scaled.shape[0], 1, input_scaled.shape[1])
            )

        prediction = model.predict(input_scaled)
        value = float(prediction[0][0])
    except Exception as e:
        logger.exception("Error making prediction")
        raise HTTPException(status_code=500, detail="Failed to make prediction") from e

    # A single contest cannot move a rating this far. Hitting this means the
    # features or the artifacts are wrong, so fail rather than return nonsense.
    if not math.isfinite(value) or abs(value) > MAX_RATING_CHANGE:
        logger.error(
            "Implausible prediction %r (limit +/-%s)", value, MAX_RATING_CHANGE
        )
        raise HTTPException(status_code=500, detail="Model produced an invalid result")

    return value
