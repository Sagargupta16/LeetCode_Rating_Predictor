import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PredictionComponent from "../components/PredictionComponent";

async function setup(name) {
  render(<PredictionComponent />);
  await screen.findByLabelText(/Participated in weekly-contest-377/i);
  if (name) {
    await userEvent.type(screen.getByLabelText(/Enter Your Username/i), name);
  }
  return screen.getByRole("button", { name: /Auto-fill/i });
}

test("auto-fill requires a username first", async () => {
  const autofill = await setup();
  fireEvent.click(autofill);

  expect(
    await screen.findByText(/Please enter a valid username/i),
  ).toBeInTheDocument();
});

test("auto-fill populates ranks from contest history", async () => {
  const autofill = await setup("testuser");
  fireEvent.click(autofill);

  expect(await screen.findByText(/Filled in 2 contests/i)).toBeInTheDocument();

  // The already-listed contest gets its real rank and is ticked
  expect(screen.getByLabelText(/Rank in weekly-contest-377/i)).toHaveValue(742);
  expect(
    screen.getByLabelText(/Participated in weekly-contest-377/i),
  ).toBeChecked();

  // A contest missing from the latest list is appended
  expect(screen.getByLabelText(/Rank in biweekly-contest-120/i)).toHaveValue(
    1310,
  );
});

test("auto-filled ranks can be submitted straight away", async () => {
  const autofill = await setup("testuser");
  fireEvent.click(autofill);
  await screen.findByText(/Filled in 2 contests/i);

  fireEvent.click(screen.getByRole("button", { name: /^Predict$/i }));

  expect(
    await screen.findByRole("heading", {
      name: /weekly-contest-377/i,
      level: 3,
    }),
  ).toBeInTheDocument();
});

test("shows a message when there is no history to fill", async () => {
  const autofill = await setup("newcomer");
  fireEvent.click(autofill);

  expect(
    await screen.findByText(/No past contests found to fill in/i),
  ).toBeInTheDocument();
});

test("surfaces an unknown username as a warning", async () => {
  const autofill = await setup("ghost");
  fireEvent.click(autofill);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /No contest history found/i,
  );
});

test("surfaces rate limiting distinctly", async () => {
  const autofill = await setup("busy");
  fireEvent.click(autofill);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /Too many requests/i,
  );
});

test("net change summary appears for multiple results", async () => {
  const autofill = await setup("testuser");
  fireEvent.click(autofill);
  await screen.findByText(/Filled in 2 contests/i);

  fireEvent.click(screen.getByRole("button", { name: /^Predict$/i }));

  expect(await screen.findByText(/Net change/i)).toBeInTheDocument();
  expect(screen.getByText("+15.25")).toBeInTheDocument();
});

test("auto-fill button is disabled while a prediction is running", async () => {
  const autofill = await setup("testuser");
  fireEvent.click(autofill);
  await screen.findByText(/Filled in 2 contests/i);

  fireEvent.click(screen.getByRole("button", { name: /^Predict$/i }));
  expect(autofill).toBeDisabled();
});
