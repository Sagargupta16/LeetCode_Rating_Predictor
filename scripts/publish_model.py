"""Build models/model.json and publish the model to the Hugging Face Hub.

models/model.json is the served network and scaler in one plain JSON file, so
the browser extension can run the model without parsing a NumPy archive. It is
derived from models/weights.npz and models/scaler.json, committed alongside
them, and tests/test_model_artifacts.py fails if it drifts.

Usage:
    python scripts/publish_model.py            # rewrite models/model.json
    python scripts/publish_model.py --upload   # also push the model repo

--upload needs a Hub login with write access (`hf auth login`, or HF_TOKEN).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from app.model_loader import load_model, load_scaler  # noqa: E402
from app.services.features import FEATURE_NAMES  # noqa: E402

MODEL_REPO = "sagargupta16/leetcode-rating-predictor"
DATASET_REPO = "sagargupta16/leetcode-contest-rating-changes"
GITHUB_URL = "https://github.com/Sagargupta16/LeetCode_Rating_Predictor"
WEB_APP_URL = "https://leetcode-rating-predictor.onrender.com"

MODELS = REPO_ROOT / "models"
MODEL_JSON = MODELS / "model.json"
METRICS = MODELS / "metrics.json"
BACKTEST = REPO_ROOT / "docs" / "backtest.md"

# Bumped whenever the meaning or order of the 15 inputs changes. The extension
# refuses a model whose feature_version it was not written for.
FEATURE_VERSION = 1
FORMAT = "leetcode-rating-predictor/dense-v1"


def _float32(value) -> float:
    # 9 significant digits round-trip a float32 exactly and keep the file small.
    return float(f"{float(value):.9g}")


def build_model_json() -> dict:
    """The served network and scaler as plain lists, in model input order."""
    # Loading through the API's own loaders first rejects anything it would.
    model = load_model(MODELS / "weights.npz")
    load_scaler(MODELS / "scaler.json")

    scaler = json.loads((MODELS / "scaler.json").read_text(encoding="utf-8"))
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    with np.load(MODELS / "weights.npz") as archive:
        meta = json.loads(str(archive["meta"]))
        layers = [
            {
                "activation": activation,
                "units": int(archive[f"b{i}"].shape[0]),
                "kernel": [[_float32(v) for v in row] for row in archive[f"w{i}"]],
                "bias": [_float32(v) for v in archive[f"b{i}"]],
            }
            for i, activation in enumerate(meta["activations"])
        ]
    return {
        "format": FORMAT,
        "feature_version": FEATURE_VERSION,
        "trained": metrics["trained"],
        "input_dim": model.input_shape[1],
        "features": list(FEATURE_NAMES),
        "scaler": {"scale": scaler["scale"], "min": scaler["min"]},
        "layers": layers,
    }


def dumps_model_json(payload: dict) -> str:
    return json.dumps(payload, separators=(",", ":")) + "\n"


def predict_from_model_json(payload: dict, features: np.ndarray) -> float:
    """Forward pass over model.json in float64, the way the extension runs it."""
    x = np.asarray(features, dtype=np.float64).reshape(-1)
    x = x * np.asarray(payload["scaler"]["scale"]) + np.asarray(
        payload["scaler"]["min"]
    )
    for layer in payload["layers"]:
        x = x @ np.asarray(layer["kernel"]) + np.asarray(layer["bias"])
        if layer["activation"] == "relu":
            x = np.maximum(x, 0)
    return float(x[0])


def _backtest_rows() -> dict[str, str]:
    """Metric -> value from the table in docs/backtest.md."""
    rows = {}
    for line in BACKTEST.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\|\s*([^|]+?)\s*\|\s*\**([^|*]+?)\**\s*\|$", line)
        if match and match.group(1) not in ("Metric", "---"):
            rows[match.group(1)] = match.group(2)
    return rows


def _backtest_date() -> str:
    match = re.search(r"on (\d{4}-\d{2}-\d{2})", BACKTEST.read_text(encoding="utf-8"))
    return match.group(1) if match else "unknown"


def render_card(link_dataset: bool) -> str:
    """Model card, with every number read from the committed metrics files."""
    m = json.loads(METRICS.read_text(encoding="utf-8"))
    bt = _backtest_rows()
    test = m["test"]
    datasets = f"datasets:\n- {DATASET_REPO}\n" if link_dataset else ""
    dataset_line = (
        f"[`{DATASET_REPO}`](https://huggingface.co/datasets/{DATASET_REPO})"
        if link_dataset
        else "the contest records collected by `scripts/update_data.py`"
    )
    feature_rows = "\n".join(
        f"| f{i} | `{name}` |" for i, name in enumerate(FEATURE_NAMES, start=1)
    )
    return f"""---
license: mit
library_name: keras
pipeline_tag: tabular-regression
tags:
- tabular-regression
- leetcode
- rating-prediction
- numpy
{datasets}---

# LeetCode Rating Predictor

Predicts how much a LeetCode contest placement moves a user's rating, from the
rank and the user's contest history. It is a small Dense network
(`15 -> 128 -> 64 -> 32 -> 1`, {m["params"]:,} parameters) that runs on plain
NumPy or JavaScript; no ML framework is needed to serve it.

It powers the [web app]({WEB_APP_URL}) and the
[browser extension]({GITHUB_URL}#browser-extension), which loads `model.json`
from this repo and adds a Predicted column to LeetCode ranking pages.
Source, training and feature code: [GitHub]({GITHUB_URL}).

## Files

| File | What |
|---|---|
| `model.json` | Network and scaler in one JSON file (what the extension loads) |
| `weights.npz`, `scaler.json` | The same network as NumPy arrays (what the API loads) |
| `model.keras` | The trained Keras model these are exported from |
| `metrics.json` | Split sizes and held-out scores of this model |
| `backtest.md` | Accuracy on recent contests of users outside the training data |

## Results

Held-out users ({m["test_users"]:,} users, {m["test_records"]:,} contest
records never seen in training), trained {m["trained"]}:

| Metric | Value |
|---|---|
| MAE | {test["mae"]} |
| RMSE | {test["rmse"]} |
| MAE of always predicting 0 | {test["zero_baseline_mae"]} |

Backtest on recent real contests of users outside the training data
(`scripts/backtest.py`, {_backtest_date()}):

| Metric | Value |
|---|---|
| Contests scored | {bt.get("Contests scored", "n/a")} |
| MAE | {bt.get("MAE", "n/a")} |
| Direction right (gain vs loss) | {bt.get("Direction right (gain vs loss)", "n/a")} |
| MAE of always predicting 0 | {bt.get("MAE of always predicting 0", "n/a")} |

## Inputs

One row per contest result, in this order. `scaler` in `model.json` maps them
to the network's range (`x * scale + min`).

| | Feature |
|---|---|
{feature_rows}

`participants` is `max(rank * 1.5, 10000)`, the form the training data was
built with, not the registered count. See `app/services/features.py` on GitHub
for the exact definitions.

## Use

```python
import json, numpy as np
from huggingface_hub import hf_hub_download

model = json.load(open(hf_hub_download("{MODEL_REPO}", "model.json")))
x = np.asarray(features, dtype=float)  # the 15 inputs above
x = x * np.asarray(model["scaler"]["scale"]) + np.asarray(model["scaler"]["min"])
for layer in model["layers"]:
    x = x @ np.asarray(layer["kernel"]) + np.asarray(layer["bias"])
    if layer["activation"] == "relu":
        x = np.maximum(x, 0)
rating_change = float(x[0])
```

## Training

Trained on {dataset_line}: {m["records"]:,} records from {m["users"]:,} users,
split by user so no user is on both sides ({m["train_records"]:,} train,
{m["val_records"]:,} validation, {m["test_records"]:,} test), {m["loss"]} loss,
seed {m["seed"]}, {m["epochs_run"]} epochs with early stopping.

## Limits

- A user's first few contests can move the rating by 100+ points; those are the
  largest errors.
- The participant count is synthetic (see Inputs), so the model does not know
  how large a contest really was.
- LeetCode can change its rating formula; the backtest is re-run weekly to
  catch drift.
"""


def upload() -> None:
    from huggingface_hub import CommitOperationAdd, HfApi
    from huggingface_hub.errors import RepositoryNotFoundError

    api = HfApi()
    api.create_repo(MODEL_REPO, repo_type="model", private=False, exist_ok=True)
    # Link the dataset from the card only once visitors can open it.
    try:
        link_dataset = not api.dataset_info(DATASET_REPO).private
    except RepositoryNotFoundError:
        link_dataset = False
    files = {
        "model.json": MODEL_JSON,
        "weights.npz": MODELS / "weights.npz",
        "scaler.json": MODELS / "scaler.json",
        "metrics.json": METRICS,
        "model.keras": REPO_ROOT / "model.keras",
        "backtest.md": BACKTEST,
    }
    operations = [
        CommitOperationAdd(path_in_repo=name, path_or_fileobj=str(path))
        for name, path in files.items()
    ]
    operations.append(
        CommitOperationAdd(
            path_in_repo="README.md",
            path_or_fileobj=render_card(link_dataset).encode("utf-8"),
        )
    )
    info = api.create_commit(
        MODEL_REPO,
        repo_type="model",
        operations=operations,
        commit_message="Publish the model trained "
        + json.loads(METRICS.read_text(encoding="utf-8"))["trained"],
    )
    print(f"published {MODEL_REPO} at {info.oid}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--upload", action="store_true", help="push to the Hub")
    args = parser.parse_args()

    # newline="\n" so the file uploaded to the Hub is LF on Windows too.
    MODEL_JSON.write_text(
        dumps_model_json(build_model_json()), encoding="utf-8", newline="\n"
    )
    print(f"wrote {MODEL_JSON.relative_to(REPO_ROOT)}")
    if args.upload:
        upload()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
