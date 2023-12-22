import React, { useState } from 'react';
import './PredictionComponent.css';

const PredictionComponent = () => {
    const [username, setUsername] = useState('');
    const [contestRank, setContestRank] = useState('');
    const [totalParticipants, setTotalParticipants] = useState('');
    const [predictionResult, setPredictionResult] = useState(null);
    const [rating, setRating] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [warning, setWarning] = useState(''); // Add warning state
    const [currentPath, setCurrentPath] = useState(window.location.href); // Add currentPath state


    const handleSubmit = async (event) => {
        event.preventDefault();
        setIsLoading(true);
        setWarning(''); // Clear previous warnings
        setPredictionResult(null); // Reset predictionResult to null
        if (window.location.href.includes('http://localhost:3000/')) {
            setCurrentPath('http://localhost:8000/api/predict');
        } else {
            setCurrentPath('https://leetcode-rating-predictor.onrender.com/api/predict');
        }

        try {
            const rank = parseInt(contestRank);
            const participants = parseInt(totalParticipants);


            if (isNaN(rank) || isNaN(participants) || rank < 0 || rank > participants || participants > 50000) {
                setWarning('Invalid input values. Rank should be between 0 and Total Participants, and Total Participants should not exceed 50,000.');
            } else {
                const response = await fetch(currentPath, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        username: username,
                        contestRank: rank,
                        totalParticipants: participants,
                    }),
                });

                if (!response.ok) {
                    // Handle the case when the username does not exist
                    if (response.status === 400) {
                        setWarning('Username does not exist.');
                    } else {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                } else {
                    const data = await response.json();
                    setPredictionResult(data.changeInRating);
                    setRating(data.rating);
                }
            }
        } catch (error) {
            console.error('There was a problem with the fetch operation:', error);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="PredictionComponent">
            <h1>Leetcode Rating Predictor</h1>
            <form onSubmit={handleSubmit} className='prediction-form'>
                <label>
                    Enter Your Username
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />
                </label>
                <label>
                    Rank in Latest Contest
                    <input
                        type="number"
                        value={contestRank}
                        onChange={(e) => setContestRank(e.target.value)}
                    />
                </label>
                <label>
                    Total Participants in Latest Contest
                    <input
                        type="number"
                        value={totalParticipants}
                        onChange={(e) => setTotalParticipants(e.target.value)}
                    />
                </label>
                <button type="submit">Submit</button>
            </form>
            <div className='prediction-info'>
                {isLoading ? (
                    <div className='loader'>Loading...</div>
                ) : (
                    predictionResult !== null && (
                        <div className='prediction-output'>
                            <p>Your Current Rating: {Math.round(rating)}</p>
                            <p>Change in Rating: {Math.round(predictionResult)}</p>
                            <p>Updated Rating: {Math.round(rating + predictionResult)}</p>
                        </div>
                    )
                )}
                {warning && <p className='warning'>{warning}</p>}
            </div>
        </div>
    );
};

export default PredictionComponent;
