from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import tensorflow as tf
import joblib
import requests
from fastapi.staticfiles import StaticFiles

# Load the trained model and the scaler
model = tf.keras.models.load_model('./model.keras')
scaler = joblib.load('./scaler.save')

# GraphQL query for fetching user contest data
query = """
query userContestRankingInfo($username: String!) {
    userContestRanking(username: $username) {
        attendedContestsCount
        rating
    }
}
"""

# Headers for the GraphQL request
headers = {"Content-Type": "application/json"}

# Fetch data for a given username using GraphQL
def fetch_data(username):
    response = requests.post(
        "https://leetcode.com/graphql",
        headers=headers,
        json={"query": query, "variables": {"username": username}}
    )
    if response.status_code == 200:
        data = response.json().get("data", {}).get("userContestRanking", [])
        if not data:
            raise ValueError("Username does not exist")
        return data
    else:
        print(f"Error fetching data for username {username}: {response.status_code}")
        raise HTTPException(status_code=500, detail="Error fetching data from LeetCode API")

# Normalize and make a prediction based on user input
def make_prediction(input_data):
    input_scaled = scaler.transform(input_data)
    input_scaled = input_scaled.reshape((input_scaled.shape[0], 1, input_scaled.shape[1]))
    prediction = model.predict(input_scaled)
    return float(prediction[0][0])  # Convert to standard Python float

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
    username: str
    contestRank: int
    totalParticipants: int

@app.post("/api/predict")
async def predict(input_data: PredictionInput):
    try:
        data = fetch_data(input_data.username)
        if not data or "rating" not in data or "attendedContestsCount" not in data:
            raise ValueError("Invalid data received from fetch_data")
        
        input1 = data["rating"]
        input2 = input_data.contestRank
        input3 = input_data.totalParticipants
        input4 = (input2 * 100) / input3 if input3 != 0 else 0
        input5 = data["attendedContestsCount"]

        prediction = make_prediction(np.array([[input1, input2, input3, input4, input5]]))
        
        output ={
            "changeInRating": prediction,
            "rating": input1,
        }
        
        return output

    except ValueError as ve:
        # Handle the custom ValueError for username not existing
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve the React build files from the 'static' directory
app.mount("/", StaticFiles(directory="./client/build", html=True), name="static")