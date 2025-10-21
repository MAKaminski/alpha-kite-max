# Contributing to Alpha Kite Max

Thank you for your interest in contributing to Alpha Kite Max! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Pull Request Process](#pull-request-process)
7. [Commit Message Guidelines](#commit-message-guidelines)
8. [Project Structure](#project-structure)
9. [Security Guidelines](#security-guidelines)

---

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to keep our community welcoming and inclusive.

---

## Getting Started

### Prerequisites

- **Git**: Version control
- **Node.js**: 18.x or higher (for frontend)
- **Python**: 3.10 or higher (for backend)
- **uv**: Python package manager (recommended)
- **Supabase Account**: For database access
- **Schwab Developer Account**: For API access (optional for frontend-only work)
- **AWS Account**: For Lambda deployment (optional)

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/alpha-kite-max.git
   cd alpha-kite-max
   ```
3. **Add upstream remote:**
   ```bash
   git remote add upstream https://github.com/MAKaminski/alpha-kite-max.git
   ```

### Environment Setup

#### Backend Setup

```bash
cd backend

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv
source .venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
uv pip install -r requirements.txt

# Copy environment template
cp ../env.example .env
# Edit .env with your credentials
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp ../.env.example .env.local
# Edit .env.local with your Supabase credentials
```

---

## Development Workflow

### Branch Strategy

We follow a simplified Git Flow:

- `main`: Production-ready code
- `develop`: Integration branch for features (if used)
- `feature/feature-name`: New features
- `fix/bug-name`: Bug fixes
- `docs/documentation-updates`: Documentation changes
- `refactor/refactor-name`: Code refactoring
- `test/test-improvements`: Test additions/improvements

### Creating a Feature Branch

```bash
# Update your local main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
```

### Working on Your Feature

1. **Make changes** in small, logical commits
2. **Test frequently** as you develop
3. **Write tests** for new functionality
4. **Update documentation** if needed
5. **Run linters** before committing

```bash
# Backend linting and formatting
cd backend
black .
isort .
pylint **/*.py

# Frontend linting
cd frontend
npm run lint
```

### Keeping Your Branch Updated

```bash
# Fetch upstream changes
git fetch upstream

# Rebase your branch on upstream main
git rebase upstream/main

# If conflicts occur, resolve them and continue
git add .
git rebase --continue
```

---

## Coding Standards

### Python (Backend)

**Style Guide**: [PEP 8](https://pep8.org/)

**Key Conventions:**
- Use `snake_case` for functions and variables
- Use `PascalCase` for classes
- Maximum line length: 100 characters
- Use type hints for function signatures
- Use Pydantic for data models (not dataclasses)
- Use `structlog` for logging
- Docstrings: Google style

**Example:**
```python
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

class TradingSignal(BaseModel):
    """Trading signal model.
    
    Attributes:
        timestamp: Signal timestamp
        direction: 'up' or 'down'
        value: Price at signal
    """
    timestamp: datetime
    direction: str
    value: float

def calculate_sma(prices: list[float], window: int = 9) -> list[float]:
    """Calculate Simple Moving Average.
    
    Args:
        prices: List of prices
        window: Moving average window size
        
    Returns:
        List of SMA values
    """
    logger.info("calculating_sma", window=window, data_points=len(prices))
    # Implementation
```

**Formatting Tools:**
- `black`: Code formatting (automatic)
- `isort`: Import sorting
- `pylint`: Linting

### TypeScript (Frontend)

**Style Guide**: [TypeScript ESLint Recommended](https://typescript-eslint.io/)

**Key Conventions:**
- Use `camelCase` for functions and variables
- Use `PascalCase` for components and types
- Use functional components with hooks (no class components)
- Prefer arrow functions
- Use explicit types (avoid `any`)
- Use interfaces for object types

**Example:**
```typescript
interface DataPoint {
  timestamp: Date;
  price: number;
  sma9: number | null;
  vwap: number | null;
}

const calculateCrosses = (data: DataPoint[]): Cross[] => {
  // Implementation
};

const EquityChart: React.FC<{ data: DataPoint[] }> = ({ data }) => {
  // Component implementation
};
```

**Formatting Tools:**
- ESLint: `npm run lint`
- Prettier (if configured): `npm run format`

### General Guidelines

1. **Minimal and modular code**: Break complex operations into small functions
2. **No verbose inline code**: Extract to helper functions
3. **Meaningful names**: Use descriptive variable and function names
4. **Comments**: Explain *why*, not *what* (code should be self-documenting)
5. **Error handling**: Always handle errors gracefully
6. **Logging**: Use structured logging, keep logs under 100KB

---

## Testing Guidelines

### Backend Testing

**Framework**: pytest

**Test Structure:**
```
backend/tests/
├── test_schwab/           # Schwab API tests
├── test_supabase/         # Database tests
├── integration/           # Integration tests
├── test_paper_trading.py  # Paper trading tests
└── conftest.py            # Shared fixtures
```

**Running Tests:**
```bash
cd backend
source .venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_schwab/test_downloader.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test
pytest tests/test_schwab/test_downloader.py::test_download_data
```

**Writing Tests:**
```python
import pytest
from schwab_integration.downloader import download_historical_data

@pytest.fixture
def mock_schwab_client():
    """Mock Schwab client for testing."""
    # Setup mock
    yield mock_client
    # Teardown

def test_download_historical_data(mock_schwab_client):
    """Test historical data download."""
    # Arrange
    ticker = "QQQ"
    days = 5
    
    # Act
    result = download_historical_data(ticker, days, mock_schwab_client)
    
    # Assert
    assert len(result) > 0
    assert result[0]['ticker'] == ticker
```

**Test Coverage Goal**: > 80%

### Frontend Testing

**Framework**: Jest + React Testing Library (if configured)

**Running Tests:**
```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm test -- --coverage
```

**Writing Tests:**
```typescript
import { render, screen } from '@testing-library/react';
import Dashboard from '@/components/Dashboard';

describe('Dashboard', () => {
  it('renders loading state', () => {
    render(<Dashboard />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
  
  it('displays chart after data loads', async () => {
    render(<Dashboard />);
    const chart = await screen.findByTestId('equity-chart');
    expect(chart).toBeInTheDocument();
  });
});
```

### Integration Testing

Test the full stack:
1. Backend downloads data from Schwab
2. Data is stored in Supabase
3. Frontend retrieves and displays data

---

## Pull Request Process

### Before Submitting

**Checklist:**
- [ ] All tests pass (`pytest` for backend, `npm test` for frontend)
- [ ] Code follows style guidelines (linters pass)
- [ ] New features have tests
- [ ] Documentation is updated (README, inline comments)
- [ ] No credentials or secrets committed
- [ ] Commit messages follow guidelines
- [ ] Branch is up to date with `main`

### Submitting a Pull Request

1. **Push your branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub:
   - Base: `main` (or `develop` if applicable)
   - Compare: `feature/your-feature-name`
   - Title: Clear, descriptive summary
   - Description: Use the PR template (if provided)

3. **PR Description Template:**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   Describe testing performed
   
   ## Screenshots (if applicable)
   Add screenshots for UI changes
   
   ## Checklist
   - [ ] Tests pass
   - [ ] Linters pass
   - [ ] Documentation updated
   ```

### Review Process

1. **Automated Checks**: CI/CD runs tests and linters
2. **Code Review**: Maintainer reviews code
3. **Feedback**: Address review comments
4. **Approval**: At least one maintainer approval required
5. **Merge**: Maintainer merges PR

### After Merge

- Delete your feature branch (locally and remotely)
- Update your local `main`:
  ```bash
  git checkout main
  git pull upstream main
  ```

---

## Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, config)
- `perf`: Performance improvements

### Examples

```bash
feat(dashboard): add date picker for navigation

Implement date picker component for easier navigation to specific dates.
Uses react-datepicker library.

Closes #123
```

```bash
fix(lambda): resolve token refresh infinite loop

Token manager was not updating expiration time correctly,
causing continuous refresh attempts.

Fixes #456
```

```bash
docs(readme): update installation instructions

Add uv package manager instructions and improve clarity.
```

### Scope Examples

- `backend`, `frontend`, `lambda`, `terraform`
- `dashboard`, `chart`, `auth`, `api`
- `tests`, `docs`, `config`

---

## Project Structure

Understanding the codebase:

```
alpha-kite-max/
├── frontend/               # Next.js application
│   ├── src/
│   │   ├── app/           # App router pages
│   │   ├── components/    # React components
│   │   └── lib/           # Utilities
├── backend/               # Python services
│   ├── schwab_integration/# Schwab API
│   ├── models/           # Data models
│   ├── tests/            # Test suites
│   ├── sys_testing/      # Utilities
│   └── lambda/           # AWS Lambda
├── infrastructure/        # Terraform
├── supabase/             # Migrations
├── shared/               # Shared types
├── context/              # Documentation
│   └── docs/            # Detailed guides
├── SECURITY.md          # Security policy
├── CONTRIBUTING.md      # This file
└── CODE_OF_CONDUCT.md   # Code of conduct
```

### Key Files

- `backend/main.py`: CLI for data download
- `backend/trading_main.py`: CLI for paper trading
- `backend/lambda/real_time_streamer.py`: Lambda handler
- `frontend/src/components/Dashboard.tsx`: Main dashboard
- `infrastructure/lambda.tf`: Lambda configuration

---

## Security Guidelines

⚠️ **Critical**: Never commit credentials!

### Pre-commit Checklist

- [ ] No API keys in code
- [ ] No tokens in code
- [ ] `.env` files not committed
- [ ] Token files not committed
- [ ] Secrets not in logs or error messages

### Using ggshield

Scan for secrets before committing:

```bash
# Install ggshield
pip install ggshield

# Scan staged changes
ggshield secret scan pre-commit

# Scan entire repo
ggshield secret scan repo .
```

### If You Accidentally Commit a Secret

1. **Rotate the secret immediately** (generate new API key/token)
2. **Remove from Git history** using BFG Repo-Cleaner or `git filter-branch`
3. **Force push** cleaned history (coordinate with team)
4. **Notify maintainers**

See [SECURITY.md](SECURITY.md) for detailed security guidelines.

---

## Getting Help

### Resources

- **Documentation**: See `/context/docs/` for detailed guides
- **Architecture**: Read [ARCHITECTURE.md](ARCHITECTURE.md)
- **Security**: Read [SECURITY.md](SECURITY.md)

### Communication

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Pull Requests**: Tag maintainers for review

### Issue Templates

When creating an issue, include:

**Bug Report:**
- Description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, versions)
- Logs or screenshots

**Feature Request:**
- Description of proposed feature
- Use case and benefits
- Implementation ideas (if any)

---

## Recognition

Contributors are recognized in:
- GitHub Contributors list
- Release notes (for significant contributions)
- Project documentation (for major features)

---

## Questions?

If you have questions about contributing, please:
1. Check existing documentation
2. Search GitHub Issues
3. Create a new issue with `question` label

Thank you for contributing to Alpha Kite Max! 🚀


