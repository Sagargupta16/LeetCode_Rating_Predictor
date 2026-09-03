"""
LeetCode Training Data Updater
===============================
Fetches contest history with solve rate and finish time for training.

Usage:
    python scripts/update_data.py                # every username in usernames.json
    python scripts/update_data.py --users 10000  # first N usernames only
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

# LeetCode throttles concurrent GraphQL reads. A throttled fetch used to be
# indistinguishable from "this account has no contests", so a rate-limited run
# silently produced a smaller dataset instead of reporting a problem.
MAX_ATTEMPTS = 4
BACKOFF_SECONDS = 2.0
MAX_RETRY_AFTER_SECONDS = 60.0
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

# A refresh that keeps less than this fraction of the records already on disk is
# treated as a failed run rather than a legitimate shrink. Contest histories only
# grow and usernames.json is fixed, so a healthy run never comes back much
# smaller -- the slack is for deleted and privated accounts.
DEFAULT_MIN_RETENTION = 0.95

# How many usernames to fetch when --users is not given.
#
# data/data.json is committed, so it lives under GitHub's 100 MB per-file hard
# limit. At the current shape (~231 bytes per record, ~36 records per user, so
# ~8.3 KB per contributing user) that ceiling lands near 12,600 users, and
# usernames.json holds 43,158 -- fetching all of them would produce roughly a
# 307 MB file that cannot be pushed at all. 8,000 attempts lands around 57 MB,
# which clears the 6,830 users behind the current dataset without approaching
# the limit. Raise this only after checking the resulting file size.
DEFAULT_MAX_USERS = 8000
GRAPHQL_QUERY = """
query userContestRankingInfo($username: String!) {
    userContestRankingHistory(username: $username) {
        attended
        rating
        ranking
        problemsSolved
        totalProblems
        finishTimeInSeconds
        contest {
            title
            startTime
        }
    }
}
"""


def _retry_delay(attempt: int, retry_after: str | None) -> float:
    """Seconds to wait before the next attempt, honouring Retry-After."""
    if retry_after:
        try:
            return min(float(retry_after), MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            logger.debug(f"Unparseable Retry-After: {retry_after!r}")
    return BACKOFF_SECONDS * (2**attempt)


def fetch_user_contest_history(session, username: str) -> list | None:
    """Fetch contest history for a user, retrying throttled and 5xx responses.

    Returns the history list, or ``None`` when the fetch itself failed. An empty
    list means the request succeeded and the account genuinely has no contest
    history. Keeping those two apart is what lets the caller tell a throttled
    run from a user with nothing to report.
    """
    for attempt in range(MAX_ATTEMPTS):
        retry_after = None
        try:
            response = session.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": GRAPHQL_QUERY, "variables": {"username": username}},
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            logger.debug(f"Network error fetching {username}: {e}")
        else:
            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError as e:
                    logger.debug(f"Parse error fetching {username}: {e}")
                    return None
                data = payload.get("data") or {}
                return data.get("userContestRankingHistory") or []
            if response.status_code not in RETRYABLE_STATUS:
                logger.debug(f"HTTP {response.status_code} fetching {username}")
                return None
            retry_after = response.headers.get("Retry-After")

        if attempt + 1 < MAX_ATTEMPTS:
            time.sleep(_retry_delay(attempt, retry_after))

    logger.debug(f"Gave up on {username} after {MAX_ATTEMPTS} attempts")
    return None


def _rolling_avg(values, default):
    """Return the mean of non-empty values, or default."""
    return sum(values) / len(values) if values else default


def _rolling_avg_positive(values, default):
    """Return the mean of positive values, or default."""
    pos = [v for v in values if v > 0]
    return sum(pos) / len(pos) if pos else default


def _build_record(rating, rank, idx, solve_rates, finish_times, ratings):
    """Build a single 15-feature training record."""
    import math

    total_participants = max(int(rank * 1.5), 10000)
    percentile = rank / total_participants

    avg_sr = _rolling_avg(solve_rates, 0.5)
    avg_ft = _rolling_avg_positive(finish_times, 3000)
    recent_sr = _rolling_avg(solve_rates[-5:], 0.5) if solve_rates else 0.5
    recent_ft = _rolling_avg_positive(finish_times[-5:], 3000)
    changes = [ratings[j] - ratings[j - 1] for j in range(1, len(ratings))]
    trend = _rolling_avg(changes[-5:], 0) if changes else 0
    max_r = max(ratings) if ratings else 1500

    return {
        "f1": rating,
        "f2": rank,
        "f3": total_participants,
        "f4": round(percentile * 100, 4),
        "f5": idx,
        "f6": round(avg_sr, 4),
        "f7": round(avg_ft, 1),
        "f8": round(recent_sr, 4),
        "f9": round(recent_ft, 1),
        "f10": round(trend, 4),
        "f11": round(max_r, 3),
        "f12": round(math.log1p(rank), 4),
        "f13": round(rating * percentile, 4),
        "f14": round(avg_sr * rating, 4),
        "f15": round(avg_ft / 5400, 4),
    }


def process_user_data(username: str, session) -> list | None:
    """Process a user's contest history into training records (15 features + output).

    Returns ``None`` when the fetch failed, so the caller can count it as a
    failure rather than as an account with no contests.
    """
    contests = fetch_user_contest_history(session, username)
    if contests is None:
        return None
    if not contests:
        return []

    data = []
    rating = 1500.0
    solve_rates, finish_times, ratings = [], [], []

    for idx, contest in enumerate(contests):
        if not contest.get("attended"):
            continue
        new_rating = contest.get("rating")
        rank = contest.get("ranking")
        if new_rating is None or rank is None or rank <= 0:
            continue

        solved = contest.get("problemsSolved", 0) or 0
        total_probs = contest.get("totalProblems", 4) or 4
        ft = contest.get("finishTimeInSeconds", 0) or 0

        record = _build_record(rating, rank, idx, solve_rates, finish_times, ratings)
        record["output"] = round(new_rating - rating, 4)
        data.append(record)

        rating = new_rating
        ratings.append(new_rating)
        solve_rates.append(solved / total_probs if total_probs > 0 else 0)
        finish_times.append(ft)

    return data


def count_records(path: Path) -> int:
    """Count the NDJSON records already in a data file."""
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def write_records(path: Path, records: list[dict]) -> None:
    """Write NDJSON via a temp file, so a crash cannot truncate the real one."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    os.replace(tmp, path)


def load_usernames(path: Path) -> list[str] | None:
    """Read the username list, or return None if it is missing."""
    try:
        with open(path, "r") as f:
            usernames = json.load(f)
    except FileNotFoundError:
        logger.error(f"{path} not found!")
        logger.info("Please ensure data/usernames.json exists")
        return None
    logger.info(f"Loaded {len(usernames)} usernames from {path}")
    return usernames


def build_session() -> requests.Session:
    """A session with the headers LeetCode's GraphQL endpoint expects."""
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
    )
    return session


def collect_records(
    usernames: list[str], session, workers: int
) -> tuple[list[dict], dict[str, int]]:
    """Fetch every user's history in parallel, returning records and a tally.

    The tally separates `failed` from `empty` so a throttled run is visible in
    the output instead of looking like a set of users with no contests.
    """
    all_data: list[dict] = []
    data_lock = threading.Lock()
    tally = {"successful": 0, "empty": 0, "failed": 0}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_user = {
            executor.submit(process_user_data, username, session): username
            for username in usernames
        }

        with tqdm(total=len(usernames), desc="Fetching data") as pbar:
            for future in as_completed(future_to_user):
                try:
                    user_data = future.result()
                except Exception as e:
                    logger.debug(f"Error: {e}")
                    tally["failed"] += 1
                else:
                    if user_data is None:
                        tally["failed"] += 1
                    elif user_data:
                        with data_lock:
                            all_data.extend(user_data)
                        tally["successful"] += 1
                    else:
                        tally["empty"] += 1
                finally:
                    pbar.update(1)

    return all_data, tally


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--users",
        type=int,
        default=DEFAULT_MAX_USERS,
        help=(
            f"How many usernames to process (default: {DEFAULT_MAX_USERS}). "
            "0 means every username, which overshoots GitHub's 100 MB file "
            "limit for data.json -- see DEFAULT_MAX_USERS"
        ),
    )
    parser.add_argument(
        "--workers", type=int, default=10, help="Concurrent fetches (default: 10)"
    )
    parser.add_argument(
        "--min-retention",
        type=float,
        default=DEFAULT_MIN_RETENTION,
        help=(
            "Refuse to overwrite data.json when the new run keeps less than this "
            f"fraction of the existing records (default: {DEFAULT_MIN_RETENTION})"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Write the new dataset even if it fails the retention check",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("LeetCode Training Data Update")
    logger.info("=" * 60)

    data_dir = Path(__file__).parent.parent / "data"
    usernames = load_usernames(data_dir / "usernames.json")
    if usernames is None:
        return 1

    if args.users > 0:
        usernames = usernames[: args.users]
    logger.info(f"Processing {len(usernames)} users with {args.workers} workers...")

    all_data, tally = collect_records(usernames, build_session(), args.workers)

    logger.info(f"\nSuccessfully processed: {tally['successful']}")
    logger.info(f"No contest history:     {tally['empty']}")
    logger.info(f"Fetch failures:         {tally['failed']}")
    logger.info(f"Total training records: {len(all_data)}")

    if not all_data:
        logger.error("No records collected; refusing to write an empty dataset.")
        return 1

    output_file = data_dir / "data.json"
    existing = count_records(output_file)
    retained = len(all_data) / existing if existing else 1.0
    if existing:
        logger.info(f"Existing records: {existing} (this run keeps {retained:.1%})")
    if retained < args.min_retention and not args.force:
        logger.error(
            f"Refusing to overwrite {output_file}: {len(all_data)} new records "
            f"against {existing} on disk ({retained:.1%}, under the "
            f"{args.min_retention:.0%} floor). {tally['failed']} of "
            f"{len(usernames)} fetches failed, which usually means LeetCode "
            "throttled the run. Re-run it, or pass --force if the shrink is "
            "intended."
        )
        return 1

    write_records(output_file, all_data)
    size_mb = output_file.stat().st_size / 1024 / 1024
    logger.info(f"\nTraining data saved to {output_file} ({size_mb:.1f} MB)")
    if size_mb > 90:
        logger.warning(
            f"{output_file.name} is {size_mb:.1f} MB, near GitHub's 100 MB "
            "per-file hard limit. Lower --users before this becomes unpushable."
        )
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
