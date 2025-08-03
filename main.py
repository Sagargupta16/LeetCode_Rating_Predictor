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
from contextlib import asynccontextmanager
from typing import List, Dict, Any
import os

# Initialize logging with better configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
model = None
scaler = None
async_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown events"""
    global model, scaler, async_client
    
    # Startup
    try:
        logger.info("Loading ML model and scaler...")
        if not os.path.exists('./model.keras'):
            raise FileNotFoundError("Model file 'model.keras' not found")
        if not os.path.exists('./scaler.save'):
            raise FileNotFoundError("Scaler file 'scaler.save' not found")
            
        model = tf.keras.models.load_model('./model.keras')
        scaler = joblib.load('./scaler.save')
        async_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Successfully loaded model, scaler, and HTTP client")
    except Exception as e:
        logger.error(f"Failed to load model or scaler: {e}")
        raise e
    
    yield
    
    # Shutdown
    if async_client:
        await async_client.aclose()
        logger.info("HTTP client closed")

app = FastAPI(
    title="LeetCode Rating Predictor API",
    description="Predict LeetCode contest rating changes using ML",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware with more restrictive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # More restrictive
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Semaphore for controlling concurrency
semaphore = asyncio.Semaphore(5)  # Reduced from 10 to 5

# Pydantic models
class Contest(BaseModel):
    name: str
    rank: int

class PredictionInput(BaseModel):
    username: str
    contests: List[Contest]

class PredictionOutput(BaseModel):
    contest_name: str
    prediction: float
    rating_before_contest: float
    rank: int
    total_participants: int
    rating_after_contest: float
    attended_contests_count: int

# GraphQL query for fetching user contest data
LEETCODE_GRAPHQL_QUERY = """
query userContestRankingInfo($username: String!) {
    userContestRanking(username: $username) {
        attendedContestsCount
        rating
    }
}
"""

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
LEETCODE_CONTEST_API_BASE = "https://leetcode.com/contest/api/ranking"

# Utility functions
async def fetch_user_data(username: str) -> Dict[str, Any]:
    """Fetch user contest data from LeetCode GraphQL API"""
    async with semaphore:
        try:
            response = await async_client.post(
                LEETCODE_GRAPHQL_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "query": LEETCODE_GRAPHQL_QUERY,
                    "variables": {"username": username}
                }
            )
            response.raise_for_status()
            data = response.json()
            
            user_data = data.get("data", {}).get("userContestRanking")
            if not user_data:
                raise ValueError(f"No contest data found for username: {username}")
                
            return user_data
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching user data: {e}")
            raise HTTPException(status_code=503, detail="Failed to fetch user data from LeetCode")
        except Exception as e:
            logger.error(f"Error fetching user data: {e}")
            raise HTTPException(status_code=400, detail=str(e))

async def fetch_contest_data(contest_name: str) -> Dict[str, Any]:
    """Fetch contest ranking data from LeetCode API"""
    async with semaphore:
        try:
            url = f"{LEETCODE_CONTEST_API_BASE}/{contest_name}/"
            response = await async_client.get(url)
            response.raise_for_status()
            contest_data = response.json()
            
            if not contest_data or contest_data == {}:
                raise ValueError(f"No data found for contest: {contest_name}")
                
            return contest_data
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching contest data: {e}")
            raise HTTPException(status_code=503, detail=f"Failed to fetch contest data for {contest_name}")
        except Exception as e:
            logger.error(f"Error fetching contest data: {e}")
            raise HTTPException(status_code=400, detail=str(e))

def make_prediction(input_data: np.ndarray) -> float:
    """Make rating prediction using the loaded ML model"""
    try:
        if model is None or scaler is None:
            raise RuntimeError("Model or scaler not loaded")
            
        input_scaled = scaler.transform(input_data)
        input_scaled = input_scaled.reshape((input_scaled.shape[0], 1, input_scaled.shape[1]))
        prediction = model.predict(input_scaled, verbose=0)
        return float(prediction[0][0])
    except Exception as e:
        logger.error(f"Error making prediction: {e}")
        raise HTTPException(status_code=500, detail="Failed to make prediction")

async def find_latest_contest_numbers() -> tuple[int, int]:
    """Find the latest biweekly and weekly contest numbers"""
    try:
        biweekly_contest = 120
        weekly_contest = 377
        max_iterations = 20  # Reduced from 100
        
        # Find latest biweekly contest
        for _ in range(max_iterations):
            try:
                response = await async_client.get(
                    f'{LEETCODE_CONTEST_API_BASE}/biweekly-contest-{biweekly_contest}/',
                    timeout=10.0
                )
                if response.json() == {}:
                    break
                biweekly_contest += 1
            except Exception:
                break
        
        # Find latest weekly contest
        for _ in range(max_iterations):
            try:
                response = await async_client.get(
                    f'{LEETCODE_CONTEST_API_BASE}/weekly-contest-{weekly_contest}/',
                    timeout=10.0
                )
                if response.json() == {}:
                    break
                weekly_contest += 1
            except Exception:
                break
        
        return biweekly_contest - 1, weekly_contest - 1
    except Exception as e:
        logger.error(f"Error finding latest contest numbers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch latest contest data")

# API Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "LeetCode Rating Predictor API is running"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "scaler_loaded": scaler is not None,
        "client_ready": async_client is not None
    }

@app.post("/api/predict", response_model=List[PredictionOutput])
async def predict(input_data: PredictionInput):
    """Predict rating changes for given contests"""
    try:
        # Validate input
        if not input_data.username.strip():
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        if not input_data.contests:
            raise HTTPException(status_code=400, detail="At least one contest must be provided")
        
        # Fetch user data
        user_data = await fetch_user_data(input_data.username)
        current_rating = user_data["rating"]
        attended_contests = user_data["attendedContestsCount"]
        
        results = []
        
        for contest in input_data.contests:
            # Validate contest data
            if contest.rank <= 0:
                raise HTTPException(status_code=400, detail=f"Invalid rank for contest {contest.name}")
            
            # Fetch contest data
            contest_data = await fetch_contest_data(contest.name)
            total_participants = contest_data.get("user_num", 0)
            
            if total_participants == 0:
                raise HTTPException(status_code=400, detail=f"No participants data for contest {contest.name}")
            
            # Calculate features
            rank_percentage = (contest.rank * 100) / total_participants
            features = np.array([[
                current_rating,
                contest.rank,
                total_participants,
                rank_percentage,
                attended_contests
            ]])
            
            # Make prediction
            rating_change = make_prediction(features)
            new_rating = current_rating + rating_change
            
            # Create result
            result = PredictionOutput(
                contest_name=contest.name,
                prediction=rating_change,
                rating_before_contest=current_rating,
                rank=contest.rank,
                total_participants=total_participants,
                rating_after_contest=new_rating,
                attended_contests_count=attended_contests
            )
            results.append(result)
            
            # Update for next iteration
            current_rating = new_rating
            attended_contests += 1
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in predict endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/contestData")
async def get_contest_data():
    """Get latest contest information"""
    try:
        biweekly_latest, weekly_latest = await find_latest_contest_numbers()
        
        # Return current contests based on schedule
        if weekly_latest % 2 == 0:
            contests = [f"weekly-contest-{weekly_latest}"]
        else:
            contests = [f"weekly-contest-{weekly_latest}", f"biweekly-contest-{biweekly_latest}"]
        
        return {"contests": contests}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in contestData endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get contest data")

# Serve static files (React app)
if os.path.exists("./client/build"):
    app.mount("/", StaticFiles(directory="./client/build", html=True), name="static")
else:
    logger.warning("React build directory not found. Static files will not be served.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
