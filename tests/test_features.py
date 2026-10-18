"""The served feature vector must match what scripts/update_data.py trains on."""

import asyncio
import math

import pytest

from app.services.features import (
    build_features,
    model_participants,
    summarize_history,
)
from app.services.leetcode import fetch_user_data
from app.utils.cache import TTLCache
from scripts.update_data import _build_record


def _entry(rating, ranking, solved=3, total=4, finish=3600, attended=True):
    return {
        "attended": attended,
        "rating": rating,
        "ranking": ranking,
        "problemsSolved": solved,
        "totalProblems": total,
        "finishTimeInSeconds": finish,
    }


HISTORY = [
    _entry(1520.0, 4000, solved=2, finish=4000),
    _entry(1555.5, 2500, solved=3, finish=3000),
    _entry(1555.5, 0, solved=0, finish=0),  # placeholder: no result
    _entry(1590.25, 1800, solved=4, finish=2800),
    _entry(1580.0, 6000, solved=0, finish=0),  # nothing accepted
    _entry(1600.0, 2100, solved=3, finish=3100),
    _entry(1610.0, 1900, solved=3, finish=3300),
    _entry(1625.0, 1500, solved=4, finish=2500),
    _entry(1640.0, 1400, solved=4, finish=2400),
]


def test_empty_history_uses_the_training_defaults():
    user = summarize_history([])
    assert user == {
        "avgSolveRate": 0.5,
        "avgFinishTime": 3000.0,
        "recentSolveRate": 0.5,
        "recentFinishTime": 3000.0,
        "ratingTrend": 0,
        "maxRating": 1500.0,
        "contestIndex": 0,
    }


def test_placeholder_entries_count_in_the_index_only():
    user = summarize_history(HISTORY)
    assert user["contestIndex"] == 9
    assert user["avgSolveRate"] == pytest.approx(
        (0.5 + 0.75 + 1.0 + 0 + 0.75 + 0.75 + 1.0 + 1.0) / 8
    )
    assert user["maxRating"] == 1640.0
    # Last 5 rated contests, then drop the zero finish time.
    assert user["recentFinishTime"] == pytest.approx((3100 + 3300 + 2500 + 2400) / 4)


@pytest.mark.parametrize("rank", [1, 900, 6666, 20000])
def test_served_features_match_the_training_record(rank):
    """Rebuild the training record for the next contest and compare all 15."""
    rated = [h for h in HISTORY if h["ranking"]]
    solve_rates = [h["problemsSolved"] / h["totalProblems"] for h in rated]
    finish_times = [h["finishTimeInSeconds"] for h in rated]
    ratings = [h["rating"] for h in rated]
    rating = ratings[-1]

    record = _build_record(
        rating, rank, len(HISTORY), solve_rates, finish_times, ratings
    )
    expected = [record[f"f{i}"] for i in range(1, 16)]

    served = build_features(
        summarize_history(HISTORY), rating, rank, len(HISTORY)
    ).ravel()
    # update_data.py rounds before writing (finish times to 1 decimal); serving
    # does not.
    assert served.tolist() == pytest.approx(expected, rel=1e-4, abs=1e-3)


def test_participant_formula():
    assert model_participants(100) == 10000
    assert model_participants(9000) == 13500
    assert build_features(summarize_history([]), 1500.0, 9000, 0)[0, 3] == (
        pytest.approx(9000 * 100 / 13500)
    )
    assert build_features(summarize_history([]), 1500.0, 9, 0)[0, 11] == (
        pytest.approx(math.log1p(9))
    )


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Client:
    def __init__(self, payload):
        self._payload = payload

    async def post(self, *args, **kwargs):
        return _Response(self._payload)


def _fetch(payload):
    return asyncio.run(
        fetch_user_data(_Client(payload), asyncio.Semaphore(1), TTLCache(), "u")
    )


def test_account_without_a_rated_contest_starts_at_1500():
    user = _fetch(
        {
            "data": {
                "matchedUser": {"username": "u"},
                "userContestRanking": None,
                "userContestRankingHistory": [_entry(1500.0, 0, solved=0)],
            }
        }
    )
    assert user["rating"] == 1500.0
    assert user["attendedContestsCount"] == 0
    assert user["contestIndex"] == 1
    assert user["avgSolveRate"] == 0.5


def test_unknown_account_is_a_client_error():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _fetch(
            {
                "data": {
                    "matchedUser": None,
                    "userContestRanking": None,
                    "userContestRankingHistory": [],
                }
            }
        )
    assert exc_info.value.status_code == 400
