"""
LeetCode Training Data Updater
===============================
Fetches contest history with solve rate and finish time for training.

Usage:
    python scripts/update_data.py
"""

import json
import logging
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


def fetch_user_contest_history(session, username):
    """Fetch contest history for a user."""
    try:
        response = session.post(
            LEETCODE_GRAPHQL_URL,
            json={"query": GRAPHQL_QUERY, "variables": {"username": username}},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            history = data.get("data", {}).get("userContestRankingHistory", [])
            if history is None:
                return []
            return history
    except requests.exceptions.RequestException as e:
        logger.debug(f"Network error fetching {username}: {e}")
    except (ValueError, KeyError) as e:
        logger.debug(f"Parse error fetching {username}: {e}")
    return []


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
        "f1": rating, "f2": rank, "f3": total_participants,
        "f4": round(percentile * 100, 4), "f5": idx,
        "f6": round(avg_sr, 4), "f7": round(avg_ft, 1),
        "f8": round(recent_sr, 4), "f9": round(recent_ft, 1),
        "f10": round(trend, 4), "f11": round(max_r, 3),
        "f12": round(math.log1p(rank), 4),
        "f13": round(rating * percentile, 4),
        "f14": round(avg_sr * rating, 4),
        "f15": round(avg_ft / 5400, 4),
    }


def process_user_data(username, session):
    """Process a user's contest history into training records (15 features + output)."""
    contests = fetch_user_contest_history(session, username)
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


def main():
    logger.info("=" * 60)
    logger.info("LeetCode Training Data Update")
    logger.info("=" * 60)

    data_dir = Path(__file__).parent.parent / "data"
    usernames_path = data_dir / "usernames.json"
    try:
        with open(usernames_path, "r") as f:
            usernames = json.load(f)
        logger.info(f"Loaded {len(usernames)} usernames from {usernames_path}")
    except FileNotFoundError:
        logger.error(f"{usernames_path} not found!")
        logger.info("Please ensure data/usernames.json exists")
        return

    print(f"\nTotal usernames available: {len(usernames)}")
    try:
        num_users = input(
            f"How many users to process? (default: min(5000, {len(usernames)})): "
        ).strip()
        num_users = int(num_users) if num_users else min(5000, len(usernames))
        num_users = max(1, min(num_users, len(usernames)))
    except (ValueError, EOFError):
        num_users = min(5000, len(usernames))

    usernames = usernames[:num_users]
    logger.info(f"\nProcessing {len(usernames)} users...")

    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
    )

    all_data = []
    data_lock = threading.Lock()
    successful = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_user = {
            executor.submit(process_user_data, username, session): username
            for username in usernames
        }

        with tqdm(total=len(usernames), desc="Fetching data") as pbar:
            for future in as_completed(future_to_user):
                try:
                    user_data = future.result()
                    if user_data:
                        with data_lock:
                            all_data.extend(user_data)
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.debug(f"Error: {e}")
                    failed += 1
                finally:
                    pbar.update(1)

                time.sleep(0.05)

    logger.info(f"\nSuccessfully processed: {successful}")
    logger.info(f"Failed/No data: {failed}")
    logger.info(f"Total training records: {len(all_data)}")

    output_file = data_dir / "data.json"
    with open(output_file, "w") as f:
        for record in all_data:
            f.write(json.dumps(record) + "\n")

    logger.info(f"\nTraining data saved to {output_file}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
