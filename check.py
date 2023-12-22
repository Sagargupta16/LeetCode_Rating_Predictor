import requests

url = 'http://127.0.0.1:8000/api/predict'
data = {
    "username": "sagargupta1610",
    "contestRank": 8000,
    "totalParticipants": 20000
}

try:
    response = requests.post(url, json=data)
    response.raise_for_status()  # Check for HTTP errors
    result = response.json()
    print("Change in Rating:", result.get("changeInRating"))
except requests.exceptions.RequestException as e:
    print("Error making the request:", str(e))
except ValueError as ve:
    print("Error decoding JSON response:", str(ve))
