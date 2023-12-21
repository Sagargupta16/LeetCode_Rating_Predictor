from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import tensorflow as tf
import joblib

# Load the trained model and the scaler
model_path = './model.keras'
scaler_path = './scaler.save'

try:
    model = tf.keras.models.load_model(model_path)
    scaler = joblib.load(scaler_path)
except Exception as e:
    print(f"Error loading model or scaler: {e}")
    # Exit if model or scaler cannot be loaded
    exit(1)

def make_prediction(input_data):
    try:
        input_scaled = scaler.transform(input_data)
        input_scaled = input_scaled.reshape((input_scaled.shape[0], 1, input_scaled.shape[1]))
        prediction = model.predict(input_scaled)
        return prediction[0][0]
    except Exception as e:
        print(f"Error during prediction: {e}")
        raise HTTPException(status_code=500, detail="Error making prediction")

app = FastAPI()

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class PredictionInput(BaseModel):
    currentRating: float
    contestRank: int

@app.post("/api/predict")
async def predict(input_data: PredictionInput):
    input1 = input_data.currentRating
    input2 = input_data.contestRank
    input3 = input1 / input2 if input2 != 0 else 0

    prediction = make_prediction(np.array([[input1, input2, input3]]))

    return {"changeInRating": prediction}

