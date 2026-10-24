"""Publish the contest records to the Hugging Face Hub as a Parquet dataset.

Turns the NDJSON that ``scripts/update_data.py`` writes (``data/data.json``,
no longer committed) into one Parquet file per split under ``data/hub/``, with
the 15 features under their real names, the rating change, an anonymous user
id and the by-user split ``scripts/train.py`` trains on. ``--upload`` pushes
those files and a dataset card to the Hub.

Usage:
    python scripts/export_dataset.py                         # write data/hub/
    python scripts/export_dataset.py --upload                # and push it
    python scripts/export_dataset.py --upload --tag training-2026-10-18

--upload needs a Hub login with write access (`hf auth login`, or HF_TOKEN).
The repo is created private; publishing it is a separate, deliberate step.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from app.services.features import FEATURE_NAMES  # noqa: E402
from scripts.publish_model import DATASET_REPO, GITHUB_URL, MODEL_REPO  # noqa: E402
from scripts.train import assign_splits, read_ndjson, user_groups  # noqa: E402

SOURCE = REPO_ROOT / "data" / "data.json"
OUT_DIR = REPO_ROOT / "data" / "hub"
SPLITS = ("train", "validation", "test")

# Same arguments scripts/train.py defaults to, so the stored split is the one a
# plain `python scripts/train.py` reproduces.
SPLIT_SEED = 42
TEST_USERS = 0.1
VAL_USERS = 0.1


def build_table(records: list[dict]):
    """One row per rated contest, columns in a fixed order."""
    import pyarrow as pa

    groups = user_groups(records)
    splits = assign_splits(groups, SPLIT_SEED, TEST_USERS, VAL_USERS)
    columns = {
        "user_id": pa.array(groups, type=pa.int32()),
        "split": pa.array(splits.tolist(), type=pa.string()),
        "contest": pa.array([r.get("contest") for r in records], type=pa.string()),
        "start_time": pa.array([r.get("start_time") for r in records], type=pa.int64()),
    }
    for i, name in enumerate(FEATURE_NAMES, start=1):
        columns[name] = pa.array([r[f"f{i}"] for r in records], type=pa.float64())
    columns["rating_change"] = pa.array(
        [r["output"] for r in records], type=pa.float64()
    )
    return pa.table(columns)


def write_splits(table, out_dir: Path) -> dict[str, int]:
    """data/<split>.parquet per split; returns the row count of each."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    (out_dir / "data").mkdir(parents=True, exist_ok=True)
    counts = {}
    for split in SPLITS:
        part = table.filter(pc.equal(table["split"], split))
        pq.write_table(part, out_dir / "data" / f"{split}.parquet", compression="zstd")
        counts[split] = part.num_rows
    return counts


def stats(table, counts: dict[str, int]) -> dict:
    users = table["user_id"].to_numpy()
    starts = [t for t in table["start_time"].to_pylist() if t]
    day = "%Y-%m-%d"
    return {
        "rows": table.num_rows,
        "users": len(np.unique(users)),
        "splits": counts,
        "first": (
            datetime.fromtimestamp(min(starts), UTC).strftime(day) if starts else None
        ),
        "last": (
            datetime.fromtimestamp(max(starts), UTC).strftime(day) if starts else None
        ),
    }


def render_card(s: dict) -> str:
    feature_rows = "\n".join(
        f"| `{name}` | f{i} |" for i, name in enumerate(FEATURE_NAMES, start=1)
    )
    span = (
        f"Contests from {s['first']} to {s['last']}."
        if s["first"]
        else "This version predates the contest and start_time columns, which are"
        " empty in it."
    )
    split_rows = "\n".join(f"| {k} | {v:,} |" for k, v in s["splits"].items())
    return f"""---
pretty_name: LeetCode contest rating changes
license: other
task_categories:
- tabular-regression
tags:
- leetcode
- rating
- competitive-programming
size_categories:
- 100K<n<1M
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train.parquet
  - split: validation
    path: data/validation.parquet
  - split: test
    path: data/test.parquet
---

# LeetCode contest rating changes

{s["rows"]:,} rated LeetCode contest results from {s["users"]:,} users: the
features a user had going into each contest, and the rating change LeetCode
then applied. {span} It is the training data of
[`{MODEL_REPO}`](https://huggingface.co/{MODEL_REPO}).

## Splits

Split by user, so no user is on both sides (seed {SPLIT_SEED}, {TEST_USERS:.0%}
of users for test, then {VAL_USERS:.0%} of the rest for validation). This is
the split `scripts/train.py` trains with.

| Split | Rows |
|---|---|
{split_rows}

## Columns

| Column | Meaning |
|---|---|
| `user_id` | Anonymous id, the same for all rows of one user in this version |
| `split` | `train`, `validation` or `test` |
| `contest` | Contest title, when the version records it |
| `start_time` | Contest start, Unix seconds, when the version records it |
| `rating_change` | Target: the rating change LeetCode applied |

Features, in model input order (`f1`..`f15` in the source code):

| Column | |
|---|---|
{feature_rows}

`participants` is `max(rank * 1.5, 10000)`: the collector never had the real
participant count, and the model is trained on this form. See
`app/services/features.py` and `scripts/update_data.py` on
[GitHub]({GITHUB_URL}) for the exact definitions.

## Source

Collected from LeetCode's public GraphQL API by `scripts/update_data.py`. No
usernames are included. LeetCode's content is subject to its Terms of Service.
"""


def upload(out_dir: Path, card: str, tag: str | None) -> str:
    from huggingface_hub import CommitOperationAdd, HfApi

    api = HfApi()
    # private only applies when the repo is created; an existing repo keeps
    # whatever visibility it has.
    api.create_repo(DATASET_REPO, repo_type="dataset", private=True, exist_ok=True)
    operations = [
        CommitOperationAdd(
            path_in_repo=f"data/{split}.parquet",
            path_or_fileobj=str(out_dir / "data" / f"{split}.parquet"),
        )
        for split in SPLITS
    ]
    operations.append(
        CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=card.encode())
    )
    info = api.create_commit(
        DATASET_REPO,
        repo_type="dataset",
        operations=operations,
        commit_message=f"Contest records, {datetime.now(UTC):%Y-%m-%d}",
    )
    if tag:
        api.create_tag(
            DATASET_REPO, repo_type="dataset", tag=tag, revision=info.oid, exist_ok=True
        )
    return info.oid


def hub_row_count(revision: str = "main") -> int:
    """Rows in the published dataset, read from the Parquet footers only."""
    import pyarrow.parquet as pq
    from huggingface_hub import HfFileSystem

    fs = HfFileSystem()
    total = 0
    for split in SPLITS:
        path = f"datasets/{DATASET_REPO}@{revision}/data/{split}.parquet"
        with fs.open(path) as f:
            total += pq.ParquetFile(f).metadata.num_rows
    return total


def read_hub_dataset(revision: str = "main"):
    """All splits of the published dataset as one Arrow table."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    parts = [
        pq.read_table(
            hf_hub_download(
                DATASET_REPO,
                f"data/{split}.parquet",
                repo_type="dataset",
                revision=revision,
            )
        )
        for split in SPLITS
    ]
    return pa.concat_tables(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", type=Path, default=SOURCE, help="NDJSON input")
    parser.add_argument("--upload", action="store_true", help="push to the Hub")
    parser.add_argument("--tag", help="also tag the uploaded commit")
    args = parser.parse_args()

    records = read_ndjson(args.source)
    table = build_table(records)
    counts = write_splits(table, OUT_DIR)
    s = stats(table, counts)
    print(f"{s['rows']:,} rows from {s['users']:,} users: {counts}")
    if args.upload:
        oid = upload(OUT_DIR, render_card(s), args.tag)
        print(f"uploaded {DATASET_REPO} at {oid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
