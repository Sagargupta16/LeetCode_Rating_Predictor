"""Feature construction shared by the API and the backtest.

The model only ever saw features built by ``scripts/update_data.py``, so the
serving path has to rebuild them the same way. Keeping that logic here, as pure
functions over a ``userContestRankingHistory`` list, means ``main.py`` and
``scripts/backtest.py`` score exactly the same feature vector: the backtest
measures the code that is actually served, not a copy of it.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np

DEFAULT_RATING = 1500.0
DEFAULT_SOLVE_RATE = 0.5
DEFAULT_FINISH_TIME = 3000.0
CONTEST_SECONDS = 5400


def _avg(values, default):
    return sum(values) / len(values) if values else default


def summarize_history(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Reduce a contest history to the per-user inputs of the model.

    ``history`` is LeetCode's ``userContestRankingHistory`` in chronological
    order. Entries with ``ranking`` 0 are placeholders (marked attended, but no
    result), which the training data skips as records yet still counts in
    feature 5. ``contestIndex`` is the position the next contest takes in the
    list, which is what the training data stores in feature 5.
    """
    attended = [h for h in history if h.get("attended") and h.get("ranking")]
    solve_rates, finish_times, ratings = [], [], []
    for h in attended:
        total_p = h.get("totalProblems", 4) or 4
        solved = h.get("problemsSolved", 0) or 0
        solve_rates.append(solved / total_p)
        finish_times.append(h.get("finishTimeInSeconds", 0) or 0)
        ratings.append(h.get("rating", DEFAULT_RATING))

    # A finish time of 0 means nothing was accepted. Like the training script,
    # take the last 5 contests first and only then drop the zeros.
    changes = [ratings[i] - ratings[i - 1] for i in range(1, len(ratings))]
    all_ft = [t for t in finish_times if t > 0]
    recent_ft = [t for t in finish_times[-5:] if t > 0]
    return {
        "avgSolveRate": _avg(solve_rates, DEFAULT_SOLVE_RATE),
        "avgFinishTime": _avg(all_ft, DEFAULT_FINISH_TIME),
        "recentSolveRate": _avg(solve_rates[-5:], DEFAULT_SOLVE_RATE),
        "recentFinishTime": _avg(recent_ft, DEFAULT_FINISH_TIME),
        "ratingTrend": _avg(changes[-5:], 0),
        "maxRating": max(ratings) if ratings else DEFAULT_RATING,
        "contestIndex": len(history),
    }


def model_participants(rank: int) -> int:
    """Participant count in the form the training data uses.

    ``scripts/update_data.py`` never had a real participant count and writes
    ``max(rank * 1.5, 10000)`` for features 3, 4 and 13. Feeding the registered
    count (30k-50k) instead puts those features outside the training
    distribution and tripled the error on a backtest of recent contests.
    """
    return max(int(rank * 1.5), 10000)


def build_features(
    user: Dict[str, Any], rating: float, rank: int, contest_index: int
) -> np.ndarray:
    """Build the (1, 15) feature row for one contest result.

    ``user`` is the output of :func:`summarize_history`. ``rating`` and
    ``contest_index`` are passed separately because a multi-contest prediction
    carries them forward from one contest to the next.
    """
    participants = model_participants(rank)
    avg_solve_rate = user["avgSolveRate"]
    avg_finish_time = user["avgFinishTime"]
    return np.array(
        [
            [
                rating,  # f1
                rank,  # f2
                participants,  # f3
                rank * 100 / participants,  # f4
                contest_index,  # f5
                avg_solve_rate,  # f6
                avg_finish_time,  # f7
                user["recentSolveRate"],  # f8
                user["recentFinishTime"],  # f9
                user["ratingTrend"],  # f10
                user["maxRating"],  # f11
                math.log1p(rank),  # f12
                rating * rank / participants,  # f13
                avg_solve_rate * rating,  # f14
                avg_finish_time / CONTEST_SECONDS,  # f15
            ]
        ]
    )
