import React, { useState } from 'react';
import './PredictionComponent.css';

const PredictionComponent = () => {
    const [currentRating, setCurrentRating] = useState('');
    const [contestRank, setContestRank] = useState('');
    const [predictionResult, setPredictionResult] = useState(null);

    const handleSubmit = async (event) => {
      event.preventDefault();
      try {
          // Update the URL to point to the FastAPI server
          const response = await fetch('http://localhost:8000/api/predict', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify({ currentRating, contestRank }),
          });
  
          if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
          }
  
          const data = await response.json();
          setPredictionResult(data.changeInRating); // Assuming 'changeInRating' is the key in the response
      } catch (error) {
          console.error('There was a problem with the fetch operation:', error);
      }
  };
  
    return (
        <div className="PredictionComponent">
            <h1>Leetcode Rating Predictor</h1>
            <form onSubmit={handleSubmit}>
                <label>
                    Current Rating:
                    <input
                        type="decimal"
                        value={currentRating}
                        onChange={(e) => setCurrentRating(e.target.value)}
                    />
                </label>
                <label>
                    Contest Rank Achieved:
                    <input
                        type="number"
                        value={contestRank}
                        onChange={(e) => setContestRank(e.target.value)}
                    />
                </label>
                <button type="submit">Submit</button>
            </form>
            {predictionResult !== null && <div className='prediction-output' >Change in rating is: {predictionResult}</div>}
        </div>
    );
};

export default PredictionComponent;
