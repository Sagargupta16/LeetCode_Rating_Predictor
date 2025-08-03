# Contributing to LeetCode Rating Predictor

Thank you for your interest in contributing to the LeetCode Rating Predictor! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/LeetCode_Rating_Predictor.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Set up the development environment (see Setup section in README)

## Development Setup

### Prerequisites
- Python 3.8+
- Node.js 14+ (for frontend development)
- Git

### Setup Steps
1. Run the setup script:
   - Windows: `setup.bat`
   - Linux/Mac: `bash setup.sh`

2. Activate virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt  # If available
   ```

## Code Style

### Python
- Follow PEP 8 style guidelines
- Use type hints where possible
- Write docstrings for functions and classes
- Use meaningful variable and function names

### JavaScript/React
- Use ES6+ features
- Follow React best practices
- Use meaningful component and variable names

## Making Changes

### Backend (Python)
- Keep functions focused and single-purpose
- Add proper error handling
- Include logging for debugging
- Write unit tests for new features

### Frontend (React)
- Create reusable components
- Handle loading states and errors
- Follow responsive design principles
- Test in multiple browsers

### Machine Learning
- Document model changes thoroughly
- Include validation metrics
- Consider model performance implications
- Update training notebooks as needed

## Testing

### Running Tests
```bash
# Backend tests (if available)
python -m pytest tests/

# Frontend tests
cd client
npm test
```

### Writing Tests
- Write unit tests for new functions
- Include integration tests for API endpoints
- Test error conditions and edge cases

## Submitting Changes

1. Ensure all tests pass
2. Update documentation if needed
3. Commit with descriptive messages:
   ```
   feat: add new rating prediction algorithm
   fix: resolve CORS issue in production
   docs: update API documentation
   ```

4. Push to your fork: `git push origin feature/your-feature-name`
5. Create a Pull Request with:
   - Clear description of changes
   - Screenshots (if UI changes)
   - Test results
   - Any breaking changes noted

## Pull Request Guidelines

- Keep PRs focused and small when possible
- Include tests for new features
- Update documentation for API changes
- Ensure CI/CD checks pass
- Request review from maintainers

## Issue Reporting

### Bug Reports
Include:
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Error messages/logs
- Screenshots if applicable

### Feature Requests
Include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Additional context

## Code Review Process

1. All submissions require review
2. Reviews focus on:
   - Code quality and style
   - Performance implications
   - Security considerations
   - Documentation completeness
   - Test coverage

3. Address review feedback promptly
4. Maintain respectful communication

## Development Guidelines

### API Development
- Follow REST principles
- Use appropriate HTTP status codes
- Include proper error responses
- Document endpoints clearly

### Machine Learning
- Version control model files appropriately
- Document training data sources
- Include model evaluation metrics
- Consider model bias and fairness

### Security
- Never commit secrets or API keys
- Validate all user inputs
- Use HTTPS in production
- Follow OWASP guidelines

## Getting Help

- Create an issue for questions
- Check existing issues and documentation
- Join community discussions
- Reach out to maintainers

Thank you for contributing to making LeetCode rating prediction better for everyone! 🚀
