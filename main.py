# %% [markdown]
# <a href="https://colab.research.google.com/github/Sagargupta16/LeetCode_Rating_Predictor/blob/main/LC_Contest_Rating_Predictor.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# %%
#Import Libraries
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

# %%
# Define GraphQL Query and Headers

# GraphQL query for fetching user contest data
query = """
query userContestRankingInfo($username: String!) {
    userContestRankingHistory(username: $username) {
        attended
        rating
        ranking
        problemsSolved
        contest {
            title
        }
    }
}
"""

# Headers for the GraphQL request
headers = {"Content-Type": "application/json"}

# %%
session = requests.Session()

def read_usernames_from_json(file_path, number_of_usernames=100):
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
        return []  # Return an empty list in case of error


# %%
def process_data(contests):
    data = []
    rating=1500
    for contest in contests:
        if contest["attended"]:
            prev_rating = rating
            rating = contest["rating"]
            ranking = contest["ranking"]
            problems_solved = contest["problemsSolved"]
            contest_type = 0 if "Weekly" in contest["contest"]["title"] else 1 if "Biweekly" in contest["contest"]["title"] else -1

            data.append([prev_rating, ranking, prev_rating / ranking if ranking != 0 else 0, problems_solved, contest_type, rating - prev_rating])
    return data

def process_batch(usernames_batch):
    data = []
    for username in usernames_batch:
        contests = fetch_data(username)
        if contests:  # Check if contests is not empty
            data.extend(process_data(contests))
    return data


usernames = read_usernames_from_json('usernames.json')

all_data = []
batch_size = 100
for i in range(0, len(usernames), batch_size):
    batch_data = process_batch(usernames[i:i + batch_size])
    all_data.extend(batch_data)
    time.sleep(1)  # Sleep to respect API rate limits


# %%
df = pd.DataFrame(all_data, columns=['input1', 'input2', 'input3', 'input4', 'input5', 'output'])
print(df)
df.to_json('data.json', orient='records', lines=True)

X = df.iloc[:, :-1].values
y = df['output'].values

scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)
joblib.dump(scaler, 'scaler.save')
X_scaled = X_scaled.reshape((X_scaled.shape[0], 1, X_scaled.shape[1]))
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.1)

# %%
# Ensure using a GPU if available
with tf.device('/device:GPU:0'):

    # Define LSTM model with cuDNN compatible configurations
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(100, activation='tanh', recurrent_activation='sigmoid', input_shape=(1, 5)),
        tf.keras.layers.Dense(1)
    ])

    # Set a custom learning rate
    learning_rate = 0.01
    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)

    # Compile the model
    model.compile(optimizer=optimizer, loss='mean_squared_error')

    # Train the model
    model.fit(X_train, y_train, epochs=10, batch_size=32)

    # Evaluate the model
    loss = model.evaluate(X_test, y_test)
    print("Test Loss:", loss)

    # Save the model in the recommended format (.keras)
    model.save('model.keras')


# %%
!pip install tensorflowjs

import tensorflow as tf
import tensorflowjs as tfjs

# Load your previously saved Keras model
model_path = '/content/model.keras'  # Replace with the path to your saved model
model = tf.keras.models.load_model(model_path)

# Directory where the TensorFlow.js model will be saved
output_dir = '/content/tfjs_model'

# Convert the model
tfjs.converters.save_keras_model(model, output_dir)



