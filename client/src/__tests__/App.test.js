import React from "react";
import { render, screen } from "@testing-library/react";
import App from "../App";

test("renders Leetcode Rating Predictor header", () => {
  render(<App />);
  const header = screen.getByText(/Leetcode Rating Predictor/i);
  expect(header).toBeInTheDocument();
});

test("renders the prediction form", () => {
  render(<App />);
  const button = screen.getByRole("button", { name: /Predict/i });
  expect(button).toBeInTheDocument();
});

test("renders username input with label", () => {
  render(<App />);
  const input = screen.getByLabelText(/Enter Your Username/i);
  expect(input).toBeInTheDocument();
});
