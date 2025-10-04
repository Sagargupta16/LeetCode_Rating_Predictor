import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import PredictionComponent from '../components/PredictionComponent';

test('renders component and validates empty username', async () => {
  render(<PredictionComponent />);

  // Input should be present
  const input = screen.getByRole('textbox');
  expect(input).toBeInTheDocument();

  // Submit without username should show a warning
  const button = screen.getByRole('button', { name: /Predict/i });
  fireEvent.click(button);

  const warning = await screen.findByText(/Please enter a valid username/i);
  expect(warning).toBeInTheDocument();
});
