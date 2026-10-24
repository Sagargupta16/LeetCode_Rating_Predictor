"""The extension's parity fixture must match what the Python code produces.

extension/inference.test.js checks the JavaScript port against
tests/fixtures/extension_parity.json. If the feature code or the model changes,
this fails until the fixture is regenerated with
``python scripts/make_parity_fixture.py``, so the JavaScript side is checked
against the current behaviour rather than a stale copy of it.
"""

import json

from scripts.make_parity_fixture import FIXTURE, build_fixture


def test_parity_fixture_matches_the_python_feature_code():
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == build_fixture()


def test_parity_fixture_covers_rated_and_unrated_contests():
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    actual = [c["expected"]["actual_change"] for c in cases]
    assert any(a is None for a in actual)
    assert any(a is not None for a in actual)
