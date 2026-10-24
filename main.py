"""FastAPI application entry point for the LeetCode Rating Predictor."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import List

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import (
    ALLOWED_ORIGINS,
    API_HOST,
    API_PORT,
    CACHE_TTL,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW,
    SCALER_PATH,
    WEIGHTS_PATH,
)
from app.model_loader import load_model, load_scaler
from app.schemas import AttendedContest, PredictionInput, PredictionOutput
from app.services.features import build_features, rated_positions, replay_features
from app.services.leetcode import (
    fetch_attended_contests,
    fetch_contest_data,
    fetch_user_data,
    find_latest_contests,
)
from app.services.prediction import make_prediction
from app.utils.cache import get_cache
from app.utils.ratelimit import RateLimiter, client_key

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
rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model and scaler on startup, close HTTP client on shutdown."""
    global model, scaler, async_client

    try:
        logger.info("Loading model and scaler...")

        if not os.path.exists(WEIGHTS_PATH):
            raise FileNotFoundError(
                f"Weights file '{WEIGHTS_PATH}' not found. "
                "Run scripts/export_model.py to generate it."
            )
        if not os.path.exists(SCALER_PATH):
            raise FileNotFoundError(
                f"Scaler file '{SCALER_PATH}' not found. "
                "Run scripts/export_model.py to generate it."
            )

        model = load_model(WEIGHTS_PATH)
        scaler = load_scaler(SCALER_PATH)

        if model.input_shape[1] != scaler.n_features_in_:
            raise ValueError(
                f"Model expects {model.input_shape[1]} features but the scaler "
                f"provides {scaler.n_features_in_}; re-export both artifacts."
            )

        async_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Successfully loaded model, scaler, and HTTP client")
    except Exception:
        logger.exception("Failed to load model or scaler")
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
    version="2.6.0",
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


@app.get(
    "/api/userContests/{username}",
    response_model=List[AttendedContest],
    responses={
        400: {"description": "Unknown username or no contest history"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "LeetCode API unavailable"},
    },
)
async def get_user_contests(username: str, request: Request):
    """List the user's recent attended contests and the ranks they actually got.

    Lets the client prefill the prediction form instead of making people look up
    their own placements.
    """
    rate_limiter.check(client_key(request))
    try:
        validated = PredictionInput(username=username, contests=[]).username
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid username") from e

    try:
        return await fetch_attended_contests(async_client, semaphore, cache, validated)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in userContests endpoint")
        raise HTTPException(
            status_code=503, detail="Failed to fetch contest history"
        ) from e


@app.post(
    "/api/predict",
    response_model=List[PredictionOutput],
    responses={
        400: {"description": "Invalid input or no contest data"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Prediction or internal error"},
        503: {"description": "LeetCode API unavailable"},
    },
)
async def predict(input_data: PredictionInput, request: Request):
    """Predict rating changes for given contests."""
    rate_limiter.check(client_key(request))
    try:
        user_data = await fetch_user_data(
            async_client, semaphore, cache, input_data.username
        )

        current_rating = user_data.get("rating")
        attended_contests = user_data.get("attendedContestsCount")
        contest_index = user_data.get("contestIndex", attended_contests)

        if current_rating is None or attended_contests is None:
            raise HTTPException(
                status_code=400, detail="Incomplete user data from LeetCode"
            )

        # Contests LeetCode already rated are part of current_rating, so they
        # are scored from the history before them and do not move the chain.
        history = user_data.get("history") or []
        rated = rated_positions(history)

        # Fetched concurrently; the semaphore still caps upstream calls.
        names = list(dict.fromkeys(c.name for c in input_data.contests))
        details = await asyncio.gather(
            *(fetch_contest_data(async_client, semaphore, cache, n) for n in names)
        )
        registered = {
            n: d.get("user_num", 0) for n, d in zip(names, details, strict=True)
        }

        results = []

        for contest in input_data.contests:
            total_participants = registered[contest.name]

            # registerUserNum from GraphQL is a pre-registration count, not
            # actual participants. Use a sensible fallback for display when
            # it is zero or smaller than the user's rank.
            if total_participants == 0:
                total_participants = max(int(contest.rank * 1.5), 10000)

            if contest.rank > total_participants:
                total_participants = int(contest.rank * 1.5)

            index = rated.get(contest.name)
            if index is not None:
                features, rating_before = replay_features(history, index, contest.rank)
                rating_change = make_prediction(model, scaler, features)
                results.append(
                    PredictionOutput(
                        contest_name=contest.name,
                        prediction=rating_change,
                        rating_before_contest=rating_before,
                        rank=contest.rank,
                        total_participants=total_participants,
                        rating_after_contest=rating_before + rating_change,
                        attended_contests_count=sum(
                            1 for h in history[:index] if h.get("attended")
                        ),
                        actual_change=history[index]["rating"] - rating_before,
                    )
                )
                continue

            # The model's participant features use the training formula
            # (see model_participants); the registered count above is display
            # only.
            features = build_features(
                user_data, current_rating, contest.rank, contest_index
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
            contest_index += 1

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in predict endpoint")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get(
    "/api/contestData",
    responses={
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Failed to get contest data"},
    },
)
async def get_contest_data(request: Request):
    """The two most recent finished contests and the next two, oldest first."""
    rate_limiter.check(client_key(request))
    try:
        contest_slugs = await find_latest_contests(async_client, cache)
        return {"contests": contest_slugs}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in contestData endpoint")
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
