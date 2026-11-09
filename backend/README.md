# ClearGuard Backend

Backend API and Filtering Intelligence service for the **ClearGuard** Android application.

## 1. Overview

ClearGuard provides system-wide domain filtering and personal protection against adult-content websites. The backend manages blocklist datasets, filtering rule versions, synchronization APIs, and future content-classification services.

## 2. Technology Stack

- **Python** 3.12+ (runtime: Python 3.14)
- **FastAPI** 0.162+
- **Pydantic & Pydantic Settings** for validation and environment configuration
- **uv** for dependency management and virtual environments
- **SQLite** for local development / **PostgreSQL** for production
- **Pytest** for testing
- **Ruff** for linting and code formatting

## 3. Project Architecture

```text
backend/
├── app/
│   ├── __init__.py           # Application package & version (0.1.0)
│   ├── main.py               # Application factory & lifespan
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py     # Versioned API v1 route aggregator
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── health.py # GET /api/v1/health endpoint
│   └── core/
│       ├── __init__.py
│       ├── config.py         # Pydantic BaseSettings configuration
│       ├── exceptions.py     # Custom exceptions & global error handlers
│       └── logging.py        # Centralized structured logging
├── tests/                    # Automated test suite
├── main.py                   # Root entry point bridge
├── pyproject.toml            # Project metadata, dependencies, tooling
├── uv.lock                   # Dependency lockfile
├── .env.example              # Environment configuration template
└── README.md
```

## 4. Getting Started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (v0.11+)
- Python 3.12 or newer

### Setup Environment

1. Copy the environment configuration template:
   ```bash
   cp .env.example .env.local
   ```
2. Sync dependencies:
   ```bash
   uv sync
   ```

### Start Local Development Server

Run the development server with live reload:
```bash
uv run fastapi dev
```

Visit:
- **Root probe:** [http://localhost:8000/](http://localhost:8000/)
- **Health check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **Interactive OpenAPI Docs (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 5. Testing & Code Quality

### Run Automated Tests

Execute the full Pytest test suite:
```bash
uv run pytest
```

### Run Linter & Formatter

Check code quality with Ruff:
```bash
uv run ruff check
uv run ruff format --check
```

Format code automatically:
```bash
uv run ruff format
```

## 6. Milestones

- **Milestone B0 — Backend Project Foundation** (`v0.1.0`): Completed.
- **Milestone B1 — Database Foundation**: Upcoming.
