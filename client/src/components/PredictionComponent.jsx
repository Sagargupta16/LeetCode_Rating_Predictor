import React, { useState, useEffect, useRef, useMemo } from "react";
import "./PredictionComponent.css";

function getApiBaseUrl() {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  if (globalThis.location?.href?.includes("localhost")) {
    return "http://localhost:8000";
  }
  return "https://leetcode-rating-predictor.onrender.com";
}

const MAX_DELTA_FOR_BAR = 60;

const PredictionComponent = () => {
  const [username, setUsername] = useState("");
  const [predictionResults, setPredictionResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingContests, setIsLoadingContests] = useState(true);
  const [isAutofilling, setIsAutofilling] = useState(false);
  const [warning, setWarning] = useState("");
  const [notice, setNotice] = useState("");
  const [contests, setContests] = useState([]);
  const apiBaseUrl = useRef(getApiBaseUrl());
  const resultsRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const fetchContests = async () => {
      try {
        const res = await fetch(`${apiBaseUrl.current}/api/contestData`, {
          headers: { "Content-Type": "application/json" },
        });
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        if (cancelled) return;
        setContests(
          data.contests.map((name) => ({ name, rank: 0, include: false })),
        );
      } catch (err) {
        console.error("Failed to load contests:", err);
        if (!cancelled) setWarning("Could not load the latest contests.");
      } finally {
        if (!cancelled) setIsLoadingContests(false);
      }
    };
    fetchContests();
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = useMemo(
    () => contests.filter((c) => c.include && c.rank > 0),
    [contests],
  );

  const toggle = (i, checked) =>
    setContests((p) =>
      p.map((c, j) => (j === i ? { ...c, include: checked, rank: 0 } : c)),
    );

  const setRank = (i, val) => {
    const v = val === "" ? 0 : Number(val);
    setContests((p) =>
      p.map((c, j) => (j === i ? { ...c, rank: Number.isNaN(v) ? 0 : v } : c)),
    );
  };

  const handleAutofill = async () => {
    if (!username.trim()) return setWarning("Please enter a valid username.");

    setIsAutofilling(true);
    setWarning("");
    setNotice("");

    try {
      const res = await fetch(
        `${apiBaseUrl.current}/api/userContests/${encodeURIComponent(username.trim())}`,
        { headers: { "Content-Type": "application/json" } },
      );

      if (!res.ok) {
        const msgs = {
          400: "No contest history found for that username.",
          429: "Too many requests. Please wait a moment.",
          503: "LeetCode API is temporarily unavailable. Try again later.",
        };
        setWarning(msgs[res.status] || `Request failed with status ${res.status}.`);
        return;
      }

      const history = await res.json();
      if (history.length === 0) {
        setNotice("No past contests found to fill in.");
        return;
      }

      setContests((prev) => {
        const merged = [...prev];
        history.forEach((h) => {
          const existing = merged.findIndex((c) => c.name === h.name);
          const filled = { name: h.name, rank: h.rank, include: true };
          if (existing >= 0) merged[existing] = filled;
          else merged.push(filled);
        });
        return merged;
      });
      setNotice(
        `Filled in ${history.length} contest${history.length === 1 ? "" : "s"} from your history.`,
      );
    } catch {
      setWarning("Network error. Please check your connection.");
    } finally {
      setIsAutofilling(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim()) return setWarning("Please enter a valid username.");

    if (selected.length === 0) {
      return setWarning(
        "Please select at least one contest and enter your rank.",
      );
    }

    setIsLoading(true);
    setWarning("");
    setNotice("");
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
        const msgs = {
          400: "Username does not exist or invalid data.",
          429: "Too many requests. Please wait a moment.",
          503: "LeetCode API is temporarily unavailable. Try again later.",
        };
        setWarning(
          msgs[res.status] || `Request failed with status ${res.status}.`,
        );
      }
    } catch {
      setWarning("Network error. Please check your connection.");
    } finally {
      setIsLoading(false);
    }
  };

  const netChange = predictionResults.reduce((sum, r) => sum + r.prediction, 0);

  return (
    <div className="glass-card">
      <header className="card-head">
        <h1 className="title">Leetcode Rating Predictor</h1>
        <p className="subtitle">
          Estimate how a contest placement moves your rating.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="form">
        <div className="field">
          <label htmlFor="username-input" className="label">
            Enter Your Username
          </label>
          <div className="input-row">
            <input
              id="username-input"
              type="text"
              className="input"
              placeholder="e.g. tourist"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="off"
              spellCheck="false"
              aria-required="true"
              aria-describedby="username-hint"
            />
            <button
              type="button"
              className="btn-secondary"
              onClick={handleAutofill}
              disabled={isAutofilling || isLoading}
            >
              {isAutofilling ? "Loading..." : "Auto-fill"}
            </button>
          </div>
          <p id="username-hint" className="hint">
            Auto-fill pulls your real ranks from past contests, so you don&apos;t
            have to look them up.
          </p>
        </div>

        {isLoadingContests && (
          <div className="skeleton-group" aria-hidden="true">
            <div className="skeleton skeleton-card" />
            <div className="skeleton skeleton-card" />
          </div>
        )}

        {contests.map((contest, i) => (
          <div
            key={contest.name}
            className={`contest-card${contest.include ? " is-active" : ""}`}
          >
            <div className="check-row">
              <input
                type="checkbox"
                id={`contest-${contest.name}`}
                className="checkbox"
                checked={contest.include}
                onChange={(e) => toggle(i, e.target.checked)}
              />
              <label
                htmlFor={`contest-${contest.name}`}
                className="input-title"
              >
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

        <button
          type="submit"
          className="btn"
          disabled={isLoading}
          aria-busy={isLoading}
        >
          {isLoading ? "Predicting..." : "Predict"}
        </button>
        {selected.length > 0 && !isLoading && (
          <p className="hint hint-center">
            Ready to predict {selected.length} contest
            {selected.length === 1 ? "" : "s"}.
          </p>
        )}
      </form>

      <section
        className="results"
        aria-label="Prediction results"
        aria-live="polite"
        ref={resultsRef}
      >
        {isLoading && (
          <output className="spinner-wrap">
            <div className="spinner" />
            <span>Loading predictions...</span>
          </output>
        )}

        {predictionResults.length > 1 && !isLoading && (
          <div className="summary">
            <span className="summary-label">Net change</span>
            <span
              className={`summary-value ${netChange >= 0 ? "positive" : "negative"}`}
            >
              {netChange >= 0 ? "+" : ""}
              {netChange.toFixed(2)}
            </span>
          </div>
        )}

        {predictionResults.map((r) => (
          <div key={r.contest_name} className="result-card">
            <h3>{r.contest_name}</h3>

            <div
              className="delta-bar"
              role="img"
              aria-label={`Rating change ${r.prediction >= 0 ? "up" : "down"} ${Math.abs(r.prediction).toFixed(2)} points`}
            >
              <span className="delta-axis" />
              <span
                className={`delta-fill ${r.prediction >= 0 ? "positive" : "negative"}`}
                style={{
                  width: `${Math.min(Math.abs(r.prediction) / MAX_DELTA_FOR_BAR, 1) * 50}%`,
                }}
              />
            </div>

            <div className="result-grid">
              <div className="stat">
                <span className="stat-label">Rank</span>
                <span className="stat-value">{r.rank}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Participants</span>
                <span className="stat-value">
                  {r.total_participants.toLocaleString()}
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">Before</span>
                <span className="stat-value">{r.rating_before_contest}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Change</span>
                <span
                  className={`stat-value ${r.prediction >= 0 ? "positive" : "negative"}`}
                >
                  {r.prediction >= 0 ? "+" : ""}
                  {r.prediction.toFixed(2)}
                </span>
              </div>
              <div className="stat highlight">
                <span className="stat-label">After</span>
                <span className="stat-value">
                  {r.rating_after_contest.toFixed(2)}
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">Contests</span>
                <span className="stat-value">{r.attended_contests_count}</span>
              </div>
            </div>
          </div>
        ))}

        {notice && <p className="notice">{notice}</p>}
        {warning && (
          <p className="warning" role="alert">
            {warning}
          </p>
        )}
      </section>
    </div>
  );
};

export default PredictionComponent;
