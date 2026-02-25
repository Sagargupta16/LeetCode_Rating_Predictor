import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PredictionComponent from "../components/PredictionComponent";

// Helper: wait for contest data to load from the mock server
async function waitForContestsToLoad() {
  await screen.findByLabelText(/Participated in weekly-contest-377/i);
}

test("renders component with username input and predict button", async () => {
  render(<PredictionComponent />);

  const input = screen.getByLabelText(/Enter Your Username/i);
  expect(input).toBeInTheDocument();

  const button = screen.getByRole("button", { name: /Predict/i });
  expect(button).toBeInTheDocument();
});

test("validates empty username on submit", async () => {
  render(<PredictionComponent />);

  const button = screen.getByRole("button", { name: /Predict/i });
  fireEvent.click(button);

  const warning = await screen.findByText(/Please enter a valid username/i);
  expect(warning).toBeInTheDocument();
});

test("loads contest data from API on mount", async () => {
  render(<PredictionComponent />);

  // The mock server returns weekly-contest-377 — the checkbox label proves it loaded
  const contestCheckbox = await screen.findByLabelText(
    /Participated in weekly-contest-377/i,
  );
  expect(contestCheckbox).toBeInTheDocument();
});

test("validates that at least one contest is selected", async () => {
  render(<PredictionComponent />);

  await waitForContestsToLoad();

  // Type a username but don't select any contest
  const input = screen.getByLabelText(/Enter Your Username/i);
  await userEvent.type(input, "testuser");

  const button = screen.getByRole("button", { name: /Predict/i });
  fireEvent.click(button);

  const warning = await screen.findByText(
    /Please select at least one contest/i,
  );
  expect(warning).toBeInTheDocument();
});

test("submit button shows loading state while predicting", async () => {
  render(<PredictionComponent />);

  await waitForContestsToLoad();

  // Type username
  const input = screen.getByLabelText(/Enter Your Username/i);
  await userEvent.type(input, "testuser");

  // Check the contest checkbox
  const checkbox = screen.getByLabelText(
    /Participated in weekly-contest-377/i,
  );
  fireEvent.click(checkbox);

  // Enter a rank
  const rankInput = screen.getByLabelText(/Rank in weekly-contest-377/i);
  await userEvent.clear(rankInput);
  await userEvent.type(rankInput, "500");

  // Submit
  const button = screen.getByRole("button", { name: /Predict/i });
  fireEvent.click(button);

  // Button should be disabled during loading
  expect(button).toBeDisabled();
});

test("displays prediction results after successful submit", async () => {
  render(<PredictionComponent />);

  await waitForContestsToLoad();

  const input = screen.getByLabelText(/Enter Your Username/i);
  await userEvent.type(input, "testuser");

  const checkbox = screen.getByLabelText(
    /Participated in weekly-contest-377/i,
  );
  fireEvent.click(checkbox);

  const rankInput = screen.getByLabelText(/Rank in weekly-contest-377/i);
  await userEvent.clear(rankInput);
  await userEvent.type(rankInput, "500");

  const button = screen.getByRole("button", { name: /Predict/i });
  fireEvent.click(button);

  // Wait for result card heading to appear
  const contestHeading = await screen.findByRole("heading", {
    name: /weekly-contest-377/i,
    level: 3,
  });
  expect(contestHeading).toBeInTheDocument();

  // Verify stat values rendered
  expect(screen.getByText("1500")).toBeInTheDocument();
  expect(screen.getByText("8,000")).toBeInTheDocument();
  expect(screen.getByText("1800")).toBeInTheDocument();
});

test("rank input is disabled when contest is not selected", async () => {
  render(<PredictionComponent />);

  await waitForContestsToLoad();

  const rankInput = screen.getByLabelText(/Rank in weekly-contest-377/i);
  expect(rankInput).toBeDisabled();

  // Check the contest
  const checkbox = screen.getByLabelText(
    /Participated in weekly-contest-377/i,
  );
  fireEvent.click(checkbox);
  expect(rankInput).not.toBeDisabled();

  // Uncheck
  fireEvent.click(checkbox);
  expect(rankInput).toBeDisabled();
});

test("warning has alert role for accessibility", async () => {
  render(<PredictionComponent />);

  const button = screen.getByRole("button", { name: /Predict/i });
  fireEvent.click(button);

  const warning = await screen.findByRole("alert");
  expect(warning).toBeInTheDocument();
});
