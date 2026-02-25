"""FastAPI application entry point for the LeetCode Rating Predictor."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import List

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import (
    ALLOWED_ORIGINS,
    API_HOST,
    API_PORT,
    CACHE_TTL,
    MODEL_PATH,
    SCALER_PATH,
)
from app.model_loader import load_keras_model
from app.schemas import PredictionInput, PredictionOutput
from app.services.leetcode import (
    fetch_contest_data,
    fetch_user_data,
    find_latest_contests,
)
from app.services.prediction import make_prediction
from app.utils.cache import get_cache

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
model = None
scaler = None
async_client = None
cache = get_cache(ttl_seconds=CACHE_TTL)
semaphore = asyncio.Semaphore(5)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model and scaler on startup, close HTTP client on shutdown."""
    global model, scaler, async_client

    try:
        logger.info("Loading ML model and scaler...")
        import joblib
        import tensorflow as tf

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file '{MODEL_PATH}' not found")
        if not os.path.exists(SCALER_PATH):
            raise FileNotFoundError(f"Scaler file '{SCALER_PATH}' not found")

        model = load_keras_model(tf, MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        async_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Successfully loaded model, scaler, and HTTP client")
    except Exception as e:
        logger.error(f"Failed to load model or scaler: {e}")
        raise

    yield

    if async_client:
        await async_client.aclose()
        logger.info("HTTP client closed")


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LeetCode Rating Predictor API",
    description="Predict LeetCode contest rating changes using ML",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api")
async def root():
    """Health check endpoint."""
    return {"message": "LeetCode Rating Predictor API is running"}


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "scaler_loaded": scaler is not None,
        "client_ready": async_client is not None,
    }


@app.post(
    "/api/predict",
    response_model=List[PredictionOutput],
    responses={
        400: {"description": "Invalid input or no contest data"},
        500: {"description": "Prediction or internal error"},
        503: {"description": "LeetCode API unavailable"},
    },
)
async def predict(input_data: PredictionInput):
    """Predict rating changes for given contests."""
    try:
        user_data = await fetch_user_data(
            async_client, semaphore, cache, input_data.username
        )

        current_rating = user_data.get("rating")
        attended_contests = user_data.get("attendedContestsCount")
        avg_solve_rate = user_data.get("avgSolveRate", 0.5)
        avg_finish_time = user_data.get("avgFinishTime", 3000)
        recent_solve_rate = user_data.get("recentSolveRate", 0.5)
        recent_finish_time = user_data.get("recentFinishTime", 3000)
        rating_trend = user_data.get("ratingTrend", 0)
        max_rating = user_data.get("maxRating", current_rating or 1500)

        if current_rating is None or attended_contests is None:
            raise HTTPException(
                status_code=400, detail="Incomplete user data from LeetCode"
            )

        results = []

        for contest in input_data.contests:
            contest_data = await fetch_contest_data(
                async_client, semaphore, cache, contest.name
            )
            total_participants = contest_data.get("user_num", 0)

            # registerUserNum from GraphQL is pre-registration count, not
            # actual participants — use a sensible fallback when it's zero or
            # smaller than the user's rank.
            if total_participants == 0:
                total_participants = max(contest.rank * 2, 10000)

            if contest.rank > total_participants:
                total_participants = contest.rank * 2

            rank_percentage = (contest.rank * 100) / total_participants
            log_rank = float(np.log1p(contest.rank))
            rating_x_pct = current_rating * (contest.rank / total_participants)
            features = np.array(
                [
                    [
                        current_rating,
                        contest.rank,
                        total_participants,  # f1-f3
                        rank_percentage,
                        attended_contests,  # f4-f5
                        avg_solve_rate,
                        avg_finish_time,  # f6-f7
                        recent_solve_rate,
                        recent_finish_time,  # f8-f9
                        rating_trend,
                        max_rating,  # f10-f11
                        log_rank,
                        rating_x_pct,  # f12-f13
                        avg_solve_rate * current_rating,  # f14
                        avg_finish_time / 5400,  # f15
                    ]
                ]
            )

            rating_change = make_prediction(model, scaler, features)
            new_rating = current_rating + rating_change

            results.append(
                PredictionOutput(
                    contest_name=contest.name,
                    prediction=rating_change,
                    rating_before_contest=current_rating,
                    rank=contest.rank,
                    total_participants=total_participants,
                    rating_after_contest=new_rating,
                    attended_contests_count=attended_contests,
                )
            )

            current_rating = new_rating
            attended_contests += 1

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in predict endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/api/contestData")
async def get_contest_data():
    """Get latest contest information."""
    try:
        contest_slugs = await find_latest_contests(async_client, cache)
        return {"contests": contest_slugs}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in contestData endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get contest data") from e


# ---------------------------------------------------------------------------
# Static files (React build)
# ---------------------------------------------------------------------------
if os.path.exists("./client/build"):
    app.mount("/", StaticFiles(directory="./client/build", html=True), name="static")
else:
    logger.warning("React build directory not found. Static files will not be served.")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)
