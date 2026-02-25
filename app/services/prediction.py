"""ML prediction service."""

import logging

import numpy as np
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def make_prediction(model, scaler, input_data: np.ndarray) -> float:
    """Make rating prediction using the loaded ML model.

    Accepts a 2D array of shape (1, num_features).  The scaler normalises
    the features and the model produces a scalar rating-change prediction.
    Works with both Dense and LSTM (1-timestep) architectures.
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

        prediction = model.predict(input_scaled, verbose=0)
        return float(prediction[0][0])
    except Exception as e:
        logger.error(f"Error making prediction: {e}")
        raise HTTPException(status_code=500, detail="Failed to make prediction")
