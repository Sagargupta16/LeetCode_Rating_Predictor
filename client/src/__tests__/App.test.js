import React from 'react';
import { render, screen } from '@testing-library/react';
import App from '../App';

test('renders Leetcode Rating Predictor header', () => {
  render(<App />);
  const header = screen.getByText(/Leetcode Rating Predictor/i);
  expect(header).toBeInTheDocument();
});
