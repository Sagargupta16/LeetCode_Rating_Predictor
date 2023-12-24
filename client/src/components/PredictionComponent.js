import React, { useState, useEffect, useCallback } from "react";
import "./PredictionComponent.css";

const PredictionComponent = () => {
  const [username, setUsername] = useState("");
  const [predictionResults, setPredictionResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [warning, setWarning] = useState("");
  const [contests, setContests] = useState([]);
  const [currentPath, setCurrentPath] = useState(window.location.href);

  const getContests = useCallback(async () => {
    try {
      const response = await fetch(`${currentPath}/api/contestData`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      } else {
        const data = await response.json();
        const initializedContests = data.contests.map((contest) => ({
          name: contest,
          rank: 0,
          include: false,
        }));
        setContests(initializedContests);
      }
    } catch (error) {
      console.error("There was a problem with the fetch operation:", error);
    }
  }, [currentPath]);

  useEffect(() => {
    if (window.location.href.includes("localhost")) {
      setCurrentPath("http://localhost:8000");
    } else {
      setCurrentPath("https://leetcode-rating-predictor.onrender.com");
    }
    getContests();
  }, [getContests]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!username.trim()) {
      setWarning("Please enter a valid username.");
      return;
    }

    const selectedContests = contests.filter(
      (contest) => contest.include && contest.rank > 0,
    );
    if (selectedContests.length === 0) {
      setWarning("Please select at least one contest and enter your rank.");
      return;
    }

    setIsLoading(true);
    setWarning("");
    setPredictionResults([]);

    try {
      const response = await fetch(`${currentPath}/api/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, contests: selectedContests }),
      });

      if (!response.ok) {
        if (response.status === 400) {
          setWarning("Username does not exist or invalid data.");
        } else {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
      } else {
        const data = await response.json();
        setPredictionResults(data);
      }
    } catch (error) {
      console.error("There was a problem with the fetch operation:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="PredictionComponent">
      <h1>Leetcode Rating Predictor</h1>
      <form onSubmit={handleSubmit} className="prediction-form">
        <div className="input-container">
          <div className="input-title">Enter Your Username</div>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        {contests.map((contest, index) => (
          <div key={index} className="contest-input">
            <div className="checkbox-container">
              <input
                type="checkbox"
                checked={contest.include}
                onChange={(e) => {
                  const newContests = [...contests];
                  newContests[index].include = e.target.checked;
                  newContests[index].rank = 0; // Reset rank if unchecked
                  setContests(newContests);
                }}
              />
              <div className="input-title">
                Participated in {contest.name} ?
              </div>
            </div>
            <div className="input-title">Your Rank in {contest.name}</div>
            <input
              type="number"
              min="1"
              value={contest.rank}
              onChange={(e) => {
                const newContests = [...contests];
                newContests[index].rank = e.target.value;
                setContests(newContests);
              }}
              disabled={!contest.include}
            />
          </div>
        ))}
        <button type="submit" disabled={isLoading}>
          Predict
        </button>
      </form>
      <div className="prediction-info">
        {isLoading ? (
          <div className="loader">Loading...</div>
        ) : (
          predictionResults.map((result, index) => (
            <div key={index} className="prediction-output">
              <p>Contest: {result.contest_name}</p>
              <p>Your Rank: {result.rank}</p>
              <p>Total Participants: {result.total_participants}</p>
              <p>Rating Before Contest: {result.rating_before_contest}</p>
              <p>Rating Change: {result.rating_after_contest}</p>
              <p>
                Rating After Contest:{" "}
                {result.rating_before_contest + result.rating_after_contest}
              </p>
              <p>Attended Contests Count: {result.attended_contests_count}</p>
            </div>
          ))
        )}
        {warning && <p className="warning">{warning}</p>}
      </div>
    </div>
  );
};

export default PredictionComponent;
