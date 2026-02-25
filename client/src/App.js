import React from "react";
import "./App.css";
import PredictionComponent from "./components/PredictionComponent";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ textAlign: "center", padding: "4rem", color: "#e2e2f0" }}>
          <h2>Something went wrong.</h2>
          <p style={{ color: "#9090a8" }}>Please refresh the page and try again.</p>
          <button
            onClick={() => this.setState({ hasError: false })}
            style={{
              marginTop: "1rem", padding: "0.5rem 1.5rem", background: "#ffa116",
              color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer",
            }}
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <div className="App">
      <ErrorBoundary>
        <PredictionComponent />
      </ErrorBoundary>
    </div>
  );
}

export default App;
