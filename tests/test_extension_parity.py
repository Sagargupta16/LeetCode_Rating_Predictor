"""The extension's parity fixture must match what the Python code produces.

extension/inference.test.js checks the JavaScript port against
tests/fixtures/extension_parity.json. If the feature code or the model changes,
this fails until the fixture is regenerated with
``python scripts/make_parity_fixture.py``, so the JavaScript side is checked
against the current behaviour rather than a stale copy of it.
"""

import json

import pytest

from scripts.make_parity_fixture import FIXTURE, build_fixture

# The prediction is a float32 forward pass, whose last digits depend on the
# platform's NumPy build (Windows and Linux CI differ around 1e-6). Everything
# else in the fixture is exact.
PREDICTION_TOLERANCE = 1e-4


def test_parity_fixture_matches_the_python_feature_code():
    stored = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fresh = build_fixture()
    assert len(stored["cases"]) == len(fresh["cases"])
    for old, new in zip(stored["cases"], fresh["cases"], strict=True):
        old_expected = dict(old.pop("expected"))
        new_expected = dict(new.pop("expected"))
        assert old == new
        assert old_expected.pop("prediction") == pytest.approx(
            new_expected.pop("prediction"), abs=PREDICTION_TOLERANCE
        )
        assert old_expected == new_expected


def test_parity_fixture_covers_rated_and_unrated_contests():
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    actual = [c["expected"]["actual_change"] for c in cases]
    assert any(a is None for a in actual)
    assert any(a is not None for a in actual)
