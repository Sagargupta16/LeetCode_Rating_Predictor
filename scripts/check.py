"""Quick smoke test for the running API server."""

import requests

url = "http://127.0.0.1:8000/api/predict"
data = {
    "username": "sagargupta1610",
    "contests": [{"name": "weekly-contest-490", "rank": 8000}],
}

try:
    response = requests.post(url, json=data)
    response.raise_for_status()
    results = response.json()
    for r in results:
        print(f"Contest: {r['contest_name']}")
        print(f"  Rating before: {r['rating_before_contest']}")
        print(f"  Predicted change: {r['prediction']:.2f}")
        print(f"  Rating after: {r['rating_after_contest']:.2f}")
except requests.exceptions.RequestException as e:
    print(f"Error making the request: {e}")
except ValueError as ve:
    print(f"Error decoding JSON response: {ve}")
