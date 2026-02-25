"""LeetCode GraphQL API client."""

import logging
from typing import Any, Dict, List

import httpx
from fastapi import HTTPException

from app.config import (
    CONTEST_NAME_RE,
    GRAPHQL_HEADERS,
    LEETCODE_GRAPHQL_URL,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GraphQL queries
# ---------------------------------------------------------------------------

USER_RANKING_QUERY = """
query userContestRankingInfo($username: String!) {
    userContestRanking(username: $username) {
        attendedContestsCount
        rating
    }
    userContestRankingHistory(username: $username) {
        attended
        problemsSolved
        totalProblems
        finishTimeInSeconds
    }
}
"""

CONTEST_DETAIL_QUERY = """
query contestDetailPage($contestSlug: String!) {
    contestDetailPage(contestSlug: $contestSlug) {
        title
        titleSlug
        registerUserNum
    }
}
"""

TOP_CONTESTS_QUERY = """
query {
    topTwoContests {
        title
        titleSlug
    }
}
"""

PAST_CONTESTS_QUERY = """
query {
    pastContests(pageNo: 1, numPerPage: 5) {
        data {
            title
            titleSlug
        }
    }
}
"""


# ---------------------------------------------------------------------------
# Public API (called from routes)
# ---------------------------------------------------------------------------


async def fetch_user_data(
    client: httpx.AsyncClient,
    semaphore,
    cache,
    username: str,
) -> Dict[str, Any]:
    """Fetch user contest data from LeetCode GraphQL API."""
    cached = cache.get(f"user:{username}")
    if cached:
        return cached

    async with semaphore:
        try:
            response = await client.post(
                LEETCODE_GRAPHQL_URL,
                headers=GRAPHQL_HEADERS,
                json={
                    "query": USER_RANKING_QUERY,
                    "variables": {"username": username},
                },
            )
            response.raise_for_status()
            data = response.json()

            user_data = data.get("data", {}).get("userContestRanking")
            if not user_data:
                raise HTTPException(
                    status_code=400,
                    detail="No contest data found for this username",
                )

            # Compute history-based features for prediction
            history = data.get("data", {}).get("userContestRankingHistory") or []
            attended = [h for h in history if h.get("attended")]
            solve_rates, finish_times, ratings = [], [], []
            for h in attended:
                total_p = h.get("totalProblems", 4) or 4
                solved = h.get("problemsSolved", 0) or 0
                solve_rates.append(solved / total_p)
                ft = h.get("finishTimeInSeconds", 0) or 0
                if ft > 0:
                    finish_times.append(ft)
                ratings.append(h.get("rating", 1500))

            def _avg(vals, default):
                return sum(vals) / len(vals) if vals else default

            user_data["avgSolveRate"] = _avg(solve_rates, 0.5)
            user_data["avgFinishTime"] = _avg(finish_times, 3000)
            user_data["recentSolveRate"] = _avg(solve_rates[-5:], 0.5)
            recent_ft = [t for t in finish_times[-5:] if t > 0]
            user_data["recentFinishTime"] = _avg(recent_ft, 3000)
            changes = [ratings[i] - ratings[i - 1] for i in range(1, len(ratings))]
            user_data["ratingTrend"] = _avg(changes[-5:], 0)
            user_data["maxRating"] = max(ratings) if ratings else 1500

            cache.set(f"user:{username}", user_data)
            return user_data
        except HTTPException:
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching user data: {e}")
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch user data from LeetCode",
            ) from e
        except Exception as e:
            logger.error(f"Error fetching user data: {e}")
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch user data from LeetCode",
            ) from e


async def fetch_contest_data(
    client: httpx.AsyncClient,
    semaphore,
    cache,
    contest_name: str,
) -> Dict[str, Any]:
    """Fetch contest data from LeetCode GraphQL API."""
    if not CONTEST_NAME_RE.match(contest_name):
        raise HTTPException(status_code=400, detail="Invalid contest name format")

    cached = cache.get(f"contest:{contest_name}")
    if cached:
        return cached

    async with semaphore:
        try:
            response = await client.post(
                LEETCODE_GRAPHQL_URL,
                headers=GRAPHQL_HEADERS,
                json={
                    "query": CONTEST_DETAIL_QUERY,
                    "variables": {"contestSlug": contest_name},
                },
            )
            response.raise_for_status()
            data = response.json()

            detail = data.get("data", {}).get("contestDetailPage")
            if not detail:
                raise HTTPException(
                    status_code=400,
                    detail=f"No data found for contest: {contest_name}",
                )

            contest_data = {
                "title": detail.get("title", contest_name),
                "titleSlug": detail.get("titleSlug", contest_name),
                "user_num": detail.get("registerUserNum", 0),
            }

            cache.set(f"contest:{contest_name}", contest_data)
            return contest_data
        except HTTPException:
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching contest data: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Failed to fetch contest data for {contest_name}",
            ) from e
        except Exception as e:
            logger.error(f"Error fetching contest data: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Failed to fetch contest data for {contest_name}",
            ) from e


async def find_latest_contests(
    client: httpx.AsyncClient,
    cache,
) -> List[str]:
    """Find the latest contest slugs via LeetCode GraphQL API."""
    cached = cache.get("latest_contests")
    if cached:
        return cached

    try:
        response = await client.post(
            LEETCODE_GRAPHQL_URL,
            headers=GRAPHQL_HEADERS,
            json={"query": TOP_CONTESTS_QUERY},
        )
        response.raise_for_status()
        data = response.json()
        top = data.get("data", {}).get("topTwoContests") or []
        slugs = [c["titleSlug"] for c in top if c.get("titleSlug")]

        if not slugs:
            response = await client.post(
                LEETCODE_GRAPHQL_URL,
                headers=GRAPHQL_HEADERS,
                json={"query": PAST_CONTESTS_QUERY},
            )
            response.raise_for_status()
            data = response.json()
            past = data.get("data", {}).get("pastContests", {}).get("data") or []
            slugs = [c["titleSlug"] for c in past[:2] if c.get("titleSlug")]

        if slugs:
            cache.set("latest_contests", slugs)
        return slugs
    except Exception as e:
        logger.error(f"Error finding latest contests: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch latest contest data"
        ) from e
