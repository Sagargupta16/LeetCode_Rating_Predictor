
# Machine Learning Model Project for Coding Contest Analysis

## Project Overview
This project encompasses the development and execution of a machine learning model focused on analyzing and predicting user performances in coding contests. Utilizing Python and various libraries, it includes functionalities for data fetching, preprocessing, training, and making predictions.

## Key Libraries
- `numpy`: For numerical computations.
- `pandas`: Data manipulation and analysis.
- `tensorflow`: Building and training neural network models.
- `sklearn`: Data preprocessing and model evaluation.
- `requests`: HTTP requests for data fetching.
- `joblib`: Saving and loading Python objects.
- `concurrent.futures`: Parallel processing.

## Data Fetching and Preprocessing
- LeetCode Contest Data: The script fetches user data from LeetCode contests using GraphQL queries.
- Data Processing: The data is structured and scaled using `MinMaxScaler` for normalization.

## Machine Learning Model
- LSTM Model: A model with LSTM (Long Short-Term Memory) layers is used, suitable for time-series data.
- Model Training: The model is trained using contest data, with a focus on predicting changes in user ratings based on their performance.

## Prediction Script
- Input Collection: The script collects user input including username, ranking, and contest information.
- Prediction: The trained model predicts the change in user rating based on the provided inputs.

## Usage Instructions
1. **Open in Colab**: The code is designed to run in a Jupyter Notebook environment, like Google Colab.
2. **Data Fetching**: Ensure you have the necessary JSON file with usernames for data fetching.
3. **Model Training**: Run the training script to train the model on your dataset.
4. **Making Predictions**: Use the prediction script to estimate changes in user ratings.

## File Structure
- `data.json`: JSON file containing the processed contest data.
- `model.keras`: Saved trained model.
- `scaler.save`: Saved MinMaxScaler object.

## Requirements
- Python 3.x
- Required Python libraries (as listed above)

## Running the Script
- Open the script in a Jupyter Notebook environment.
- Execute the cells in sequence, starting from data fetching to model training.
- For predictions, run the main function and follow the prompts.

## Note
- Ensure you have a stable internet connection for data fetching.
- The model's accuracy depends on the quality and quantity of the data.

## Conclusion
This project demonstrates the application of machine learning in analyzing and predicting user performance in competitive coding platforms. It serves as a useful tool for users to gauge their progress and anticipate future performances.
