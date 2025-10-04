"""
Simple LeetCode Training Data Updater
======================================
Updates training data by fetching latest contest history for existing usernames.

Usage:
    python update_data_simple.py
"""

import json
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging

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
            return data.get("data", {}).get("userContestRankingHistory", [])
    except Exception as e:
        logger.debug(f"Error fetching {username}: {e}")
    return []


def process_user_data(username, session):
    """Process a user's contest history into training data"""
    contests = fetch_user_contest_history(session, username)
    if not contests:
        return []

    data = []
    rating = 1500.0

    for idx, contest in enumerate(contests):
        if contest.get("attended"):
            new_rating = contest.get("rating", rating)
            rank = contest.get("ranking", 0)

            # Estimate total participants based on rank
            total_participants = max(rank * 1.5, 10000)
            percentile = (rank / total_participants) if total_participants > 0 else 0
            rating_change = new_rating - rating

            record = {
                "input1": rating,
                "input2": rank,
                "input3": int(total_participants),
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
    try:
        with open("usernames.json", "r") as f:
            usernames = json.load(f)
        logger.info(f"Loaded {len(usernames)} usernames from usernames.json")
    except FileNotFoundError:
        logger.error("usernames.json not found!")
        logger.info("Please ensure usernames.json exists in the current directory")
        return

    # Ask how many users to process
    print(f"\nTotal usernames available: {len(usernames)}")
    try:
        num_users = input(
            f"How many users to process? (default: min(5000, {len(usernames)})): "
        ).strip()
        num_users = int(num_users) if num_users else min(5000, len(usernames))
    except:
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

    # Process users
    all_data = []
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
    output_file = "data.json"
    with open(output_file, "w") as f:
        for record in all_data:
            f.write(json.dumps(record) + "\n")

    logger.info(f"\n✅ Training data saved to {output_file}")
    logger.info("=" * 60)
    logger.info("Update complete!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Open LC_Contest_Rating_Predictor.ipynb")
    logger.info("2. Run all cells to retrain the model")
    logger.info("3. Restart your API server")


if __name__ == "__main__":
    main()
