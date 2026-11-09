# ClearGuard Backend

Backend API and Filtering Intelligence service for the **ClearGuard** Android application.

## 1. Overview

ClearGuard provides system-wide domain filtering and personal protection against adult-content websites. The backend manages blocklist datasets, filtering rule versions, synchronization APIs, and content-classification services.

## 2. Technology Stack

- **Python** 3.12+ (runtime: Python 3.14)
- **FastAPI** 0.162+
- **SQLAlchemy 2** (Async ORM) & **Alembic** for schema migrations
- **SQLite + aiosqlite** for local development & integration testing
- **PostgreSQL + asyncpg** for production deployment
- **Pydantic & Pydantic Settings** for validation and environment-driven configuration
- **uv** for high-performance dependency management and virtual environments
- **Pytest** for testing
- **Ruff** for linting and code formatting

## 3. Project Architecture

```text
backend/
├── alembic/                  # Schema migration scripts and async environment
│   ├── env.py                # Async Alembic execution with batch mode
│   ├── script.py.mako        # Migration template
│   └── versions/             # Versioned schema migration files
├── app/
│   ├── __init__.py           # Application package & version (0.2.0)
│   ├── main.py               # Application factory & lifespan
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── router.py     # Versioned API v1 route aggregator
│   │       └── endpoints/
│   │           └── health.py # GET /api/v1/health endpoint
│   ├── core/
│   │   ├── config.py         # Pydantic BaseSettings & URL normalization
│   │   ├── database.py       # Async engine, session providers & transaction scopes
│   │   ├── database_errors.py# SQLAlchemy to domain error translation
│   │   ├── exceptions.py     # Custom exceptions & global error handlers
│   │   └── logging.py        # Centralized structured logging
│   ├── models/
│   │   ├── __init__.py       # Model exports
│   │   └── base.py           # DeclarativeBase, UUIDMixin, TimestampMixin
│   └── repositories/
│       ├── __init__.py       # Repository exports
│       └── base.py           # Generic async BaseRepository with savepoint isolation
├── tests/                    # Automated test suite
├── alembic.ini               # Alembic configuration
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

### Database Operations & Migrations

- **Apply Migrations**:
  ```bash
  uv run alembic upgrade head
  ```
- **Generate a New Migration**:
  ```bash
  uv run alembic revision --autogenerate -m "describe_changes"
  ```
- **Inspect Current Revision**:
  ```bash
  uv run alembic current
  ```
- **Roll Back Last Migration**:
  ```bash
  uv run alembic downgrade -1
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

## 5. Database Architecture & Production Path

### Local Persistence (SQLite)
- Local development utilizes an asynchronous SQLite database via `aiosqlite`.
- URL format: `sqlite+aiosqlite:///./clearguard.db` (auto-normalized from standard `sqlite:///` URLs).
- SQLite tables utilize batch-mode migrations (`render_as_batch=True`) to handle table alterations safely.

### Production Path (PostgreSQL)
- Set `DATABASE_URL` in production environment variables (e.g. Cloud Run, Kubernetes, AWS ECS):
  ```bash
  DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/clearguard_prod
  ```
- The backend automatically detects standard `postgresql://` and `postgres://` connection strings and normalizes them to use `asyncpg`.
- Models utilize portable UUID primary keys (`sqlalchemy.types.Uuid`) ensuring seamless parity between SQLite character storage and native PostgreSQL `UUID` column types.
- Deterministic constraint naming conventions (`pk_`, `fk_`, `uq_`, `ck_`, `ix_`) ensure consistent schema migrations across both database engines.

## 6. Domain & Blocklist Intelligence

### Domain Normalization & Validation
- **Normalization Pipeline**: Strips protocols (`http://`, `https://`, `ftp://`), userinfo, ports (`:8080`), and path/query/fragment strings. Strips leading `www.` while preserving subdomains (`cdn.media.site.com`).
- **Internationalized Domain Names (IDN)**: Automatically encodes Unicode domains to ASCII Punycode (`münchen.de` -> `xn--mnchen-3ya.de`) using UTS-46 standards.
- **RFC 1035 / RFC 1123 Validation**: Validates total length (1–253 chars), label lengths (1–63 chars), alphanumeric characters with internal hyphens, valid non-numeric top-level domains (minimum 2 characters), and explicitly rejects raw IPv4/IPv6 addresses.

### Multi-Format Feed Ingestion
- **Formats Supported**: `/etc/hosts` (e.g. `0.0.0.0 domain.com`, `127.0.0.1 domain.com`), Adblock Plus syntax (e.g. `||domain.com^`), and plain domain-per-line lists.
- **Sanitization**: Automatically ignores comments (`#`, `!`), inline comments, whitespace, and loopback addresses (`127.0.0.1`, `::1`, `localhost`).
- **Bulk Processing**: Resilient bulk import with batch duplicate detection, deduplicating both in-flight inputs and pre-existing database records.

### Blocklist Organization & Versioning
- **Entities**: Supports multiple blocklists (`Blocklist`), associations (`BlocklistDomain`), and immutable version releases (`BlocklistVersion`).
- **Cryptographic Versioning**: Releases compute a deterministic SHA-256 hash over alphabetically sorted, newline-delimited active domains, allowing Android clients to verify feed integrity and detect delta updates.
- **Semantic Versioning**: Automatically calculates semver patch progressions (e.g. `1.0.0` -> `1.0.1`) while supporting explicit versions and release changelogs.

## 7. Testing & Code Quality

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

## 8. Milestones

- **Milestone B0 — Backend Project Foundation** (`v0.1.0`): Completed.
- **Milestone B1 — Database Foundation** (`v0.2.0`): Completed.
- **Milestone B2 — Adult Domain Management** (`v0.3.0`): Completed.
- **Milestone B3 — Blocklist REST API** (`v0.4.0`): Upcoming.
