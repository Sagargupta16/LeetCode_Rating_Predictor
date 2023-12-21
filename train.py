# Import Libraries
import concurrent.futures
import json
import numpy as np
import pandas as pd
import requests
import tensorflow as tf
import time
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping
import joblib
from concurrent.futures import ThreadPoolExecutor

# Define GraphQL Query and Headers
query = """
query userContestRankingInfo($username: String!) {
    userContestRankingHistory(username: $username) {
        attended
        rating
        ranking
    }
}
"""
headers = {"Content-Type": "application/json"}

# Session Initialization
session = requests.Session()

# Functions for Fetching and Processing Data
def read_usernames_from_json(file_path, number_of_usernames=40000):
    with open(file_path, 'r') as file:
        all_usernames = json.load(file)
        return all_usernames[:number_of_usernames]

def fetch_data(username):
    response = requests.post(
        "https://leetcode.com/graphql",
        headers=headers,
        json={"query": query, "variables": {"username": username}}
    )
    if response.status_code == 200:
        return response.json().get("data", {}).get("userContestRankingHistory", [])
    else:
        print(f"Error fetching data for username {username}: {response.status_code}")
        return []

def process_data(contests):
    data = []
    rating = 1500
    for contest in contests:
        if contest["attended"]:
            prev_rating = rating
            rating = contest["rating"]
            ranking = contest["ranking"]
            data.append([prev_rating, ranking, prev_rating / ranking if ranking != 0 else 0, rating - prev_rating])
    return data

def process_batch_parallel(usernames_batch, max_workers=100):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(fetch_data, usernames_batch)
    data = []
    for contests in results:
        if contests:
            data.extend(process_data(contests))
    return data

# Fetch and Process User Data
usernames = read_usernames_from_json('./usernames.json')
all_data = []
batch_size = 1000
for i in range(0, len(usernames), batch_size):
    batch_data = process_batch_parallel(usernames[i:i + batch_size])
    all_data.extend(batch_data)
    time.sleep(1)  # Sleep to respect API rate limits

# Convert Data to DataFrame and Scale
df = pd.DataFrame(all_data, columns=['input1', 'input2', 'input3', 'output'])
print(df)
df.to_json('data.json', orient='records', lines=True)

X = df.iloc[:, :-1].values
y = df['output'].values

scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)
joblib.dump(scaler, 'scaler.save')
X_scaled = X_scaled.reshape((X_scaled.shape[0], 1, X_scaled.shape[1]))
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3)

# Ensure using a GPU if available and Define LSTM model
with tf.device('/device:GPU:0'):
    model = Sequential([
        LSTM(500, activation='tanh', recurrent_activation='sigmoid', input_shape=(1, 3)),
        Dense(1)
    ])
    optimizer = tf.keras.optimizers.Adam(learning_rate=0.01)
    model.compile(optimizer=optimizer, loss='mean_squared_error')
    model.fit(X_train, y_train, epochs=10, batch_size=32)
    loss = model.evaluate(X_test, y_test)
    print("Test Loss:", loss)
    model.save('model.keras')

# Convert to TensorFlow.js Model (if needed)
# !pip install tensorflowjs
# import tensorflowjs as tfjs
# model_path = '/content/model.keras'
# output_dir = '/content/tfjs_model'
# tfjs.converters.save_keras_model(model, output_dir)

# Prediction Function
def get_user_input():
    print("Enter the input values:")
    input1 = float(input("Enter your previous rating: "))
    input2 = float(input("Enter your ranking: "))
    input3 = input1 / input2 if input2 != 0 else 0
    return np.array([[input1, input2, input3]])

def make_prediction(input_data):
    input_scaled = scaler.transform(input_data)
    input_scaled = input_scaled.reshape((input_scaled.shape[0], 1, input_scaled.shape[1]))
    prediction = model.predict(input_scaled)
    return prediction[0][0]

def main():
    user_input = get_user_input()
    prediction = make_prediction(user_input)
    print(f"Predicted change in rating: {prediction}")

if __name__ == "__main__":
    main()
