"""Write tests/fixtures/extension_parity.json from the API's own feature code.

The browser extension rebuilds the 15 features and runs the network in
JavaScript. This fixture is what the Python path produces for a few synthetic
contest histories; extension/inference.test.js checks the JavaScript port
against it, and tests/test_extension_parity.py fails if the fixture no longer
matches the Python code or the committed model.

Usage:
    python scripts/make_parity_fixture.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.model_loader import load_model, load_scaler  # noqa: E402
from app.services.features import (  # noqa: E402
    DEFAULT_RATING,
    build_features,
    rated_positions,
    replay_features,
    summarize_history,
)

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "extension_parity.json"


def _entry(slug, rating, ranking, solved, finish, attended=True, total=4):
    return {
        "attended": attended,
        "rating": rating,
        "ranking": ranking,
        "problemsSolved": solved,
        "totalProblems": total,
        "finishTimeInSeconds": finish,
        "contest": {"titleSlug": slug},
    }


# Covers the cases the feature code branches on: an unranked placeholder, a
# contest with nothing accepted (finish time 0), a non-attended entry, and more
# than five rated contests so the "recent" windows differ from the full ones.
HISTORY = [
    _entry("weekly-contest-500", 1521.4, 3100, 2, 4100),
    _entry("biweekly-contest-150", 1563.9, 2400, 3, 3650),
    _entry("weekly-contest-501", 1563.9, 0, 0, 0),
    _entry("weekly-contest-502", 1612.2, 1500, 3, 2900),
    _entry("biweekly-contest-151", 1590.7, 5200, 1, 0),
    _entry("weekly-contest-503", 1590.7, 4000, 1, 2500, attended=False),
    _entry("weekly-contest-504", 1633.0, 1900, 3, 3300),
    _entry("weekly-contest-505", 1702.5, 700, 4, 2100),
    _entry("biweekly-contest-152", 1688.1, 2600, 2, 4800),
    _entry("weekly-contest-506", 1655.3, 4400, 2, 5100),
]

CASES = [
    ("contest not rated yet", HISTORY, 1655.3, "weekly-contest-530", 1200),
    ("rated contest replayed", HISTORY, 1655.3, "weekly-contest-505", 700),
    ("rated first contest", HISTORY, 1655.3, "weekly-contest-500", 3100),
    ("first contest, no history", [], DEFAULT_RATING, "weekly-contest-530", 8000),
    (
        "only an unranked placeholder",
        [_entry("weekly-contest-529", 1500.0, 0, 0, 0)],
        DEFAULT_RATING,
        "weekly-contest-530",
        2500,
    ),
]


def build_fixture() -> dict:
    model = load_model(REPO_ROOT / "models" / "weights.npz")
    scaler = load_scaler(REPO_ROOT / "models" / "scaler.json")
    cases = []
    for name, history, current_rating, contest, rank in CASES:
        index = rated_positions(history).get(contest)
        if index is None:
            summary = summarize_history(history)
            features = build_features(
                summary, current_rating, rank, summary["contestIndex"]
            )
            rating_before, actual = current_rating, None
        else:
            features, rating_before = replay_features(history, index, rank)
            actual = history[index]["rating"] - rating_before
        prediction = float(model.predict(scaler.transform(features))[0][0])
        cases.append(
            {
                "name": name,
                "history": history,
                "current_rating": current_rating,
                "contest": contest,
                "rank": rank,
                "expected": {
                    "features": [float(v) for v in features[0]],
                    "rating_before": rating_before,
                    "prediction": prediction,
                    "actual_change": actual,
                },
            }
        )
    return {"model": "models/model.json", "cases": cases}


def dumps_fixture(fixture: dict) -> str:
    return json.dumps(fixture, indent=2) + "\n"


def main() -> int:
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(dumps_fixture(build_fixture()), encoding="utf-8")
    print(f"wrote {FIXTURE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
