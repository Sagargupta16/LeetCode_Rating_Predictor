
# LeetCode Contest Rating Predictor

## Project Overview
This deep learning project offers a sophisticated solution for predicting user ratings in LeetCode coding contests. It blends a Python-based FastAPI backend with a React front-end, delivering a comprehensive and user-friendly platform. Leveraging thousands of data points, the system utilizes an LSTM neural network model to analyze and predict contest ratings, representing a significant advancement in competitive coding analytics.

## Key Features
- **Deep Learning Model**: Uses an LSTM network to accurately predict ratings from extensive contest data.
- **Extensive Data Analysis**: Analyzes thousands of data points to ensure precise predictions.
- **Interactive Web Interface**: A React-based front-end for an engaging user experience.
- **Automated Data Fetching**: Utilizes GraphQL for efficient data collection from LeetCode.
- **Data Preprocessing**: Implements advanced techniques like MinMaxScaler for data normalization.
- **Backend Server**: FastAPI backend for efficient data handling and response.
- **Scalable Architecture**: Designed to handle large datasets and complex neural network operations.

## Data Fetching and Preprocessing
- **LeetCode Contest Data**: Automated fetching using GraphQL queries.
- **Normalization and Structuring**: Utilizing MinMaxScaler for data consistency.

## Machine Learning Model
- **LSTM Neural Network**: Optimized for time-series data analysis in competitive coding scenarios.
- **Training and Evaluation**: In-depth training using a vast dataset for accurate prediction capabilities.

## Prediction Script
- **User Input Handling**: Efficiently collects user data like username, ranking, and contest details.
- **Rating Prediction**: Employs the trained model to forecast rating changes.

## Requirements
- **Python 3.x**: Essential for running the backend and scripts.
- **Python Libraries**: As listed in `requirements.txt`.
- **Stable Internet Connection**: For data fetching and web application functionality.
- **Jupyter Notebook Environment**: For model training using `LC_Contest_Rating_Predictor.ipynb`.

## File Structure
- `client/`: Contains the React front-end application.
- `LC_Contest_Rating_Predictor.ipynb`: Jupyter Notebook for LSTM model training.
- `data.json`, `usernames.json`: JSON files with processed data and user information.
- `model.keras`: The trained deep learning model.
- `scaler.save`: Serialized object for data scaling.
- `main.py`, `check.py`: FastAPI backend and utility scripts.
- `requirements.txt`: Dependencies for Python environment.

## Usage
1. **Web-Based Method**:
   - Start the FastAPI backend by running `python main.py`.
   - Navigate to the `client` folder and run `npm start` to launch the React app.
   - Interact with the web interface for data input and receive predictions.
2. **Colab Method**:
   - Open `LC_Contest_Rating_Predictor.ipynb` in Google Colab.
   - Run the notebook cells to train the model and perform predictions.

## Notes
- Ensure a stable internet connection for seamless operation.
- Accuracy and performance depend on data quality and volume.
- Refer to in-code comments for detailed guidance on each component.

## Conclusion
The LeetCode Contest Rating Predictor is a cutting-edge deep learning tool designed to analyze and predict user performance in coding contests. It stands out for its ability to process large-scale data and provide accurate forecasts, making it a valuable asset for competitive coders seeking to enhance their skills and strategies.
