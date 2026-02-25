"""
Simple LeetCode Training Data Updater
======================================
Updates training data by fetching latest contest history for existing usernames.

Usage:
    python update_data_simple.py
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
        contest {
            title
            startTime
        }
    }
}
"""


def fetch_user_contest_history(session, username):
    """Fetch contest history for a user"""
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


def process_user_data(username, session):
    """Process a user's contest history into training data"""
    contests = fetch_user_contest_history(session, username)
    if not contests:
        return []

    data = []
    rating = 1500.0

    for idx, contest in enumerate(contests):
        if not contest.get("attended"):
            continue

        new_rating = contest.get("rating")
        rank = contest.get("ranking")
        if new_rating is None or rank is None or rank <= 0:
            continue

        # Estimate total participants based on rank
        total_participants = max(int(rank * 1.5), 10000)
        percentile = rank / total_participants
        rating_change = new_rating - rating

        record = {
            "input1": rating,
            "input2": rank,
            "input3": total_participants,
            "input4": percentile,
            "input5": idx,
            "output": rating_change,
        }

        data.append(record)
        rating = new_rating

    return data


def main():
    logger.info("=" * 60)
    logger.info("LeetCode Training Data Update")
    logger.info("=" * 60)

    # Load existing usernames
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

    # Ask how many users to process
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

    # Setup session
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
    )

    # Process users with thread-safe data collection
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

                time.sleep(0.05)  # Rate limiting

    logger.info(f"\nSuccessfully processed: {successful}")
    logger.info(f"Failed/No data: {failed}")
    logger.info(f"Total training records: {len(all_data)}")

    # Save to file
    output_file = data_dir / "data.json"
    with open(output_file, "w") as f:
        for record in all_data:
            f.write(json.dumps(record) + "\n")

    logger.info(f"\nTraining data saved to {output_file}")
    logger.info("=" * 60)
    logger.info("Update complete!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Open LC_Contest_Rating_Predictor.ipynb")
    logger.info("2. Run all cells to retrain the model")
    logger.info("3. Restart your API server")


if __name__ == "__main__":
    main()
