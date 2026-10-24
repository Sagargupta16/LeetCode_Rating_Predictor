"""Retrain the rating model with a split that keeps each user on one side.

The notebook splits individual contest records at random, so one user's
contests land in both train and test and the test score flatters the model.
This script splits by *user* instead and fits the scaler on the training users
only, then writes the same artifacts the notebook does:

    model.keras, scaler.save   (Keras + joblib, project root)
    models/metrics.json        (split sizes and held-out scores)

Run ``python scripts/export_model.py`` afterwards to refresh the NumPy artifacts
the API serves.

The data comes from the Hub dataset by default (``--data hub``), which carries
a user id and the split per row, so the split is the published one. A local
``data/data.json`` from ``scripts/update_data.py`` works too. Older copies of it
store no user id, but each user's records are written contiguously and chain: a
record's rating is the previous record's rating plus its rating change, so a
break in that chain is a user boundary. On the 2026-10-18 dataset the chain
breaks (8,182) match the records that look like a first contest (rating 1500,
no history) one for one.

Usage:
    pip install -r requirements-ml.txt
    python scripts/train.py                                  # latest Hub data
    python scripts/train.py --revision training-2026-10-18   # a tagged version
    python scripts/train.py --data data/data.json            # a local fetch
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.services.features import FEATURE_NAMES  # noqa: E402

NUM_FEATURES = 15
CHAIN_TOLERANCE = 0.01
# Rating changes are tens of points, so a delta of 10 keeps Huber quadratic for
# ordinary errors and linear only for the first-contest swings of 100+.
HUBER_DELTA = 10.0

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def read_ndjson(path: Path) -> list[dict]:
    """The records ``scripts/update_data.py`` writes, one JSON object per line."""
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def user_groups(records: list[dict]) -> np.ndarray:
    """A user group id per record: ``user_id`` when present, else chain breaks."""
    if records and all("user_id" in r for r in records):
        return np.array([r["user_id"] for r in records])
    groups = []
    group = -1
    previous = None
    for record in records:
        expected = previous["f1"] + previous["output"] if previous else None
        if expected is None or abs(record["f1"] - expected) > CHAIN_TOLERANCE:
            group += 1
        groups.append(group)
        previous = record
    return np.array(groups)


def split_users(groups: np.ndarray, fraction: float, rng) -> np.ndarray:
    """Boolean mask selecting ``fraction`` of the users (all their records)."""
    users = np.unique(groups)
    chosen = rng.choice(users, size=round(len(users) * fraction), replace=False)
    return np.isin(groups, chosen)


def assign_splits(
    groups: np.ndarray, seed: int, test_users: float, val_users: float
) -> np.ndarray:
    """ "train", "validation" or "test" per record, split by user.

    The Hub dataset stores this column, so it has to stay the exact procedure
    the 2026-10-18 model was trained with: test users first, then validation
    users from the rest, from one generator seeded with ``seed``.
    """
    rng = np.random.default_rng(seed)
    test = split_users(groups, test_users, rng)
    rest = ~test
    val = np.zeros_like(test)
    val[rest] = split_users(groups[rest], val_users, rng)
    return np.where(test, "test", np.where(val, "validation", "train"))


def load_records(
    data: str, revision: str, seed: int, test_users: float, val_users: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Features, targets, user groups and split labels for ``--data``."""
    if data == "hub":
        from scripts.export_dataset import read_hub_dataset

        table = read_hub_dataset(revision)
        x = np.column_stack([table[name].to_numpy() for name in FEATURE_NAMES])
        return (
            x,
            table["rating_change"].to_numpy(),
            table["user_id"].to_numpy(),
            np.asarray(table["split"].to_pylist()),
        )

    records = read_ndjson(REPO_ROOT / data)
    groups = user_groups(records)
    x = np.array([[r[f"f{i}"] for i in range(1, NUM_FEATURES + 1)] for r in records])
    y = np.array([r["output"] for r in records])
    return x, y, groups, assign_splits(groups, seed, test_users, val_users)


def build_model(tf, loss: str):
    """Dense(128)->Dropout(0.3)->Dense(64)->Dropout(0.2)->Dense(32)->Dense(1)."""
    layers = tf.keras.layers
    model = tf.keras.Sequential(
        [
            layers.Input(shape=(NUM_FEATURES,)),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.3),
            layers.Dense(64, activation="relu"),
            layers.Dropout(0.2),
            layers.Dense(32, activation="relu"),
            layers.Dense(1),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0005),
        loss=tf.keras.losses.Huber(delta=HUBER_DELTA) if loss == "huber" else "mse",
        metrics=["mae"],
    )
    return model


def scores(predicted: np.ndarray, actual: np.ndarray) -> dict[str, float]:
    error = predicted - actual
    return {
        "mae": round(float(np.mean(np.abs(error))), 2),
        "rmse": round(float(np.sqrt(np.mean(error**2))), 2),
        "zero_baseline_mae": round(float(np.mean(np.abs(actual))), 2),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--data",
        default="hub",
        help="'hub' for the Hub dataset, or an NDJSON path from update_data.py",
    )
    parser.add_argument(
        "--revision", default="main", help="Hub dataset branch, tag or commit"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-users", type=float, default=0.1)
    parser.add_argument("--val-users", type=float, default=0.1)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument(
        "--loss",
        choices=["mse", "huber"],
        default="mse",
        help="training loss (mse matches the notebook)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    import joblib
    import tensorflow as tf
    from sklearn.preprocessing import MinMaxScaler

    tf.keras.utils.set_random_seed(args.seed)

    x, y, groups, splits = load_records(
        args.data, args.revision, args.seed, args.test_users, args.val_users
    )
    users = len(np.unique(groups))
    logger.info(f"{len(y):,} records from {users:,} users")

    train, val, test = (splits == name for name in ("train", "validation", "test"))
    logger.info(
        f"train {train.sum():,} / val {val.sum():,} / test {test.sum():,} records"
    )

    scaler = MinMaxScaler()
    x_train = scaler.fit_transform(x[train])
    x_val = scaler.transform(x[val])
    x_test = scaler.transform(x[test])

    model = build_model(tf, args.loss)
    stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=args.patience, restore_best_weights=True
    )
    history = model.fit(
        x_train,
        y[train],
        validation_data=(x_val, y[val]),
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=[stop],
        verbose=2,
    )

    test_scores = scores(model.predict(x_test, verbose=0).ravel(), y[test])
    logger.info(f"held-out users: {test_scores}")

    model.save(REPO_ROOT / "model.keras")
    joblib.dump(scaler, REPO_ROOT / "scaler.save")

    metrics = {
        "trained": datetime.now(UTC).strftime("%Y-%m-%d"),
        "split": "by user",
        "loss": args.loss,
        "seed": args.seed,
        "records": int(len(y)),
        "users": users,
        "train_records": int(train.sum()),
        "val_records": int(val.sum()),
        "test_records": int(test.sum()),
        "test_users": int(len(np.unique(groups[test]))),
        "epochs_run": len(history.history["loss"]),
        "params": int(model.count_params()),
        "test": test_scores,
    }
    out = REPO_ROOT / "models" / "metrics.json"
    out.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    logger.info(f"wrote model.keras, scaler.save and {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
