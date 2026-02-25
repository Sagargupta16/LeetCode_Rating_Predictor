import React, { useState, useEffect, useRef } from "react";
import "./PredictionComponent.css";

function getApiBaseUrl() {
  if (process.env.REACT_APP_API_BASE_URL) {
    return process.env.REACT_APP_API_BASE_URL;
  }
  // eslint-disable-next-line no-restricted-globals
  if (typeof window !== "undefined" && window.location.href.includes("localhost")) {
    return "http://localhost:8000";
  }
  return "https://leetcode-rating-predictor.onrender.com";
}

const PredictionComponent = () => {
  const [username, setUsername] = useState("");
  const [predictionResults, setPredictionResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [warning, setWarning] = useState("");
  const [contests, setContests] = useState([]);
  const apiBaseUrl = useRef(getApiBaseUrl());

  useEffect(() => {
    const fetchContests = async () => {
      try {
        const res = await fetch(`${apiBaseUrl.current}/api/contestData`, {
          headers: { "Content-Type": "application/json" },
        });
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        setContests(data.contests.map((name) => ({ name, rank: 0, include: false })));
      } catch (err) {
        console.error("Failed to load contests:", err);
      }
    };
    fetchContests();
  }, []);

  const toggle = (i, checked) =>
    setContests((p) => p.map((c, j) => (j === i ? { ...c, include: checked, rank: 0 } : c)));

  const setRank = (i, val) => {
    const v = val === "" ? 0 : Number(val);
    setContests((p) => p.map((c, j) => (j === i ? { ...c, rank: Number.isNaN(v) ? 0 : v } : c)));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim()) return setWarning("Please enter a valid username.");

    const selected = contests.filter((c) => c.include && c.rank > 0);
    if (selected.length === 0) return setWarning("Please select at least one contest and enter your rank.");

    setIsLoading(true);
    setWarning("");
    setPredictionResults([]);

    try {
      const res = await fetch(`${apiBaseUrl.current}/api/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, contests: selected }),
      });

      if (res.ok) {
        setPredictionResults(await res.json());
      } else {
        const msgs = { 400: "Username does not exist or invalid data.", 503: "LeetCode API is temporarily unavailable. Try again later." };
        setWarning(msgs[res.status] || `Request failed with status ${res.status}.`);
      }
    } catch {
      setWarning("Network error. Please check your connection.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-card">
      <h1 className="title">Leetcode Rating Predictor</h1>

      <form onSubmit={handleSubmit} className="form">
        <div className="field">
          <label htmlFor="username-input" className="label">Enter Your Username</label>
          <input
            id="username-input"
            type="text"
            className="input"
            placeholder="e.g. tourist"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            aria-required="true"
          />
        </div>

        {contests.map((contest, i) => (
          <div key={contest.name} className="contest-card">
            <div className="check-row">
              <input
                type="checkbox"
                id={`contest-${contest.name}`}
                className="checkbox"
                checked={contest.include}
                onChange={(e) => toggle(i, e.target.checked)}
              />
              <label htmlFor={`contest-${contest.name}`} className="input-title">
                Participated in {contest.name} ?
              </label>
            </div>
            <label htmlFor={`rank-${contest.name}`} className="label">
              Your Rank in {contest.name}
            </label>
            <input
              id={`rank-${contest.name}`}
              type="number"
              className="input"
              min="1"
              placeholder="Enter rank"
              value={contest.rank}
              onChange={(e) => setRank(i, e.target.value)}
              disabled={!contest.include}
              aria-label={`Rank in ${contest.name}`}
            />
          </div>
        ))}

        <button type="submit" className="btn" disabled={isLoading} aria-busy={isLoading}>
          {isLoading ? "Predicting..." : "Predict"}
        </button>
      </form>

      <section className="results" aria-label="Prediction results" aria-live="polite">
        {isLoading && (
          <output className="spinner-wrap">
            <div className="spinner" />
            <span>Loading predictions...</span>
          </output>
        )}

        {predictionResults.map((r) => (
          <div key={r.contest_name} className="result-card">
            <h3>{r.contest_name}</h3>
            <div className="result-grid">
              <div className="stat">
                <span className="stat-label">Rank</span>
                <span className="stat-value">{r.rank}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Participants</span>
                <span className="stat-value">{r.total_participants.toLocaleString()}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Before</span>
                <span className="stat-value">{r.rating_before_contest}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Change</span>
                <span className={`stat-value ${r.prediction >= 0 ? "positive" : "negative"}`}>
                  {r.prediction >= 0 ? "+" : ""}
                  {r.prediction.toFixed(2)}
                </span>
              </div>
              <div className="stat highlight">
                <span className="stat-label">After</span>
                <span className="stat-value">{r.rating_after_contest.toFixed(2)}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Contests</span>
                <span className="stat-value">{r.attended_contests_count}</span>
              </div>
            </div>
          </div>
        ))}

        {warning && <p className="warning" role="alert">{warning}</p>}
      </section>
    </div>
  );
};

export default PredictionComponent;
