from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import tensorflow as tf
import joblib
from fastapi.staticfiles import StaticFiles
import httpx
import asyncio
import logging
# Initialize logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()
# Global cache for contest data
contest_data_cache = {}

# Load the trained model and the scaler with error handling
try:
    model = tf.keras.models.load_model('./model.keras')
    scaler = joblib.load('./scaler.save')
except Exception as e:
    logging.error(f"Error loading model or scaler: {e}")
    raise e

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

# Shared httpx.AsyncClient instance
async_client = httpx.AsyncClient()

# Semaphore for controlling concurrency
semaphore = asyncio.Semaphore(10)

# Define the PredictionInput class
class PredictionInput(BaseModel):
    username: str
    contests : list

# Function Definitions
# ---------------------

async def fetch_page(url):
    async with semaphore:
        async with async_client.get(url) as response:
            response.raise_for_status()
            return response.json()


async def fetch_data(username):
    try:
        response = await async_client.post(
            "https://leetcode.com/graphql",
            headers=headers,
            json={"query": query, "variables": {"username": username}}
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("userContestRanking", [])
    except Exception as e:
        logging.error(f"Error fetching data from LeetCode API: {e}")
        raise HTTPException(status_code=400, detail=str(e))

def make_prediction(input_data):
    try:
        input_scaled = scaler.transform(input_data)
        input_scaled = input_scaled.reshape((input_scaled.shape[0], 1, input_scaled.shape[1]))
        prediction = model.predict(input_scaled)
        return float(prediction[0][0])  # Convert to standard Python float
    except Exception as e:
        logging.error(f"Error making prediction: {e}")
        raise e

async def update_latest_contest_data(biweekly_contest, weekly_contest):
    try:
        max_iterations = 100  # Example: set a maximum number of iterations
        iteration = 0
        while iteration < max_iterations:
            response = await async_client.get(f'https://leetcode.com/contest/api/ranking/biweekly-contest-{biweekly_contest}/')
            if response.json() == {}:
                break
            biweekly_contest += 1
            iteration += 1

        iteration = 0
        while iteration < max_iterations:
            response = await async_client.get(f'https://leetcode.com/contest/api/ranking/weekly-contest-{weekly_contest}/')
            if response.json() == {}:
                break
            weekly_contest += 1
            iteration += 1

        return biweekly_contest - 1, weekly_contest - 1
    except Exception as e:
        logging.error(f"Error updating latest contest data: {e}")
        raise e

# API Endpoints
# -------------

@app.post("/api/predict")
async def predict(input_data: PredictionInput):
    try:
        data = await fetch_data(input_data.username)
        if not data or "rating" not in data or "attendedContestsCount" not in data:
            raise ValueError("Invalid data received from fetch_data")

        input1 = data["rating"]
        input5 = data["attendedContestsCount"]
        
        contests = []

        for contest in input_data.contests:
            print(f"Contest: {contest}")
            if "name" not in contest:
                raise ValueError("Contest does not contain 'name' attribute.")
            
            response = await async_client.get(f'https://leetcode.com/contest/api/ranking/{contest["name"]}/')
            contest_data = response.json()
            
            if "rank" not in contest:
                raise ValueError("Contest does not contain 'rank' attribute.")
            
            input2 = int(contest["rank"])
            input3 = contest_data.get("user_num", 0)
            input4 = (input2 * 100) / input3 if input3 != 0 else 0
            prediction = make_prediction(np.array([[input1, input2, input3, input4, input5]]))
            
            output ={
                "contest_name": contest["name"],
                "prediction": prediction,
                "rating_before_contest": input1,
                "rank": input2,
                "total_participants": input3,
                "rating_after_contest": prediction,
                "attended_contests_count": input5,
            }
            contests.append(output)
            input1 = input1 + prediction
            input5 = input5 + 1
            
        return contests

    except ValueError as ve:
        logging.error(f"Value error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        logging.error(f"Generic error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contestData")
async def contestData():
    try:
        biweekly_contest = 120  # Ideally, these should be stored and updated in a database or file
        weekly_contest = 377
        biweekly_contest, weekly_contest = await update_latest_contest_data(biweekly_contest, weekly_contest)
        
        if weekly_contest%2 == 0:
            return {"contests": [f"weekly-contest-{weekly_contest}"]}
        else :
            return {"contests": [f"weekly-contest-{weekly_contest}", f"biweekly-contest-{biweekly_contest}"]}     
            
    except Exception as e:
        logging.error(f"Error in contestData: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Serve the React build files from the 'static' directory
app.mount("/", StaticFiles(directory="./client/build", html=True), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
