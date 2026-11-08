# ClearGuard Backend — Development Plan

**Project:** ClearGuard  
**Component:** Backend API and Filtering Intelligence  
**Language:** Python  
**Framework:** FastAPI  
**Development Environment:** Python + uv  
**Database:** SQLite (development) / PostgreSQL (production)  
**Document Status:** Initial Development Roadmap  
**Initial Version:** 0.1.0

---

## 1. Purpose

This document defines the development roadmap for the ClearGuard backend.

The backend provides the APIs and supporting services required by the ClearGuard Android application.

Development follows a milestone-driven approach. Every milestone is divided into implementation phases, and every phase contains individually executable tasks.

The project owner controls task selection, implementation approval, architecture decisions and milestone completion.

AI coding agents are implementation assistants and must not independently expand the project scope or proceed to future tasks.

## 2. Backend Objectives

The backend must:

- Provide a reliable REST API for ClearGuard.
- Maintain adult-domain blocklist data.
- Provide versioned filtering rules.
- Allow Android applications to retrieve updated blocklists.
- Support synchronization without requiring real-time backend availability.
- Maintain structured and validated domain information.
- Support future content-classification services.
- Protect application and user data.
- Support local development and production deployment.

The backend is a supporting component of the protection system. It must not become a dependency for real-time DNS filtering.

## 3. Technology Stack

| Area | Technology |
|---|---|
| Language | Python |
| Framework | FastAPI |
| Python Version | To be established during foundation |
| Package Manager | uv |
| Database (Development) | SQLite |
| Database (Production) | PostgreSQL |
| ORM | SQLAlchemy 2 |
| Database Migrations | Alembic |
| Data Validation | Pydantic |
| API Documentation | OpenAPI / Swagger UI |
| Testing | Pytest |
| HTTP Client | HTTPX |
| Containerization | Docker |
| Code Formatting | Ruff |
| Type Checking | mypy (subject to setup) |
| CI/CD | GitHub Actions |

All dependency versions must be verified against official documentation before adoption.

## 4. Development and Production Environments

### 4.1 Local Development

Local development uses SQLite.

The database should be stored in a local development location and excluded from Git.

The backend should be executable locally without requiring a production database or cloud service.

### 4.2 Production

Production uses PostgreSQL.

The production database will be created and managed by the project owner through the selected hosting provider.

The production database URL will be provided when deployment and integration are ready.

Database configuration must be environment-driven.

The application must not hardcode database credentials or database URLs.

### 4.3 Environment Files

The project uses:

```text
backend/
├── .env.local
├── .env.production
├── .env.example
└── ...
```

Strict rules:

- `.env.local` is owned and managed by the project owner.
- `.env.production` is owned and managed by the project owner.
- AI agents MUST NOT read, modify, overwrite, delete or commit either private environment file.
- AI agents MAY create and update `.env.example`.
- `.env.example` must contain variable names, safe example values and configuration descriptions.
- Actual secrets must never appear in source code, logs, tests or documentation.
- Both private environment files must be excluded from Git.
- Database configuration must support SQLite locally and PostgreSQL in production.

The project owner is responsible for supplying production credentials.

## 5. Database Design Principles

### 5.1 Primary Keys

All backend database entities must use UUID primary keys.

Requirements:

- Use UUID values for primary keys.
- Use consistent UUID representation across models.
- Use appropriate foreign-key relationships.
- Generate UUIDs safely.
- Never use sequential integer IDs for primary keys.

### 5.2 Database Compatibility

Database models and migrations must support both:

- SQLite for local development.
- PostgreSQL for production.

Avoid database-specific implementations unless necessary and documented.

Use SQLAlchemy 2 conventions and Alembic migrations.

### 5.3 Data Integrity

All database entities must have:

- Explicit field types.
- Appropriate constraints.
- Appropriate indexes.
- Defined relationships.
- Clear ownership and lifecycle rules.

Database migrations must be tested before being considered complete.

## 6. Development Rules

### 6.1 Task Execution

- Implement only the task explicitly assigned by the project owner.
- Do not implement future milestone features prematurely.
- Inspect existing files before modifying them.
- Do not overwrite project-owner-managed environment files.
- Avoid unnecessary dependencies and abstractions.
- Keep business logic separate from API routing.
- Explain significant architectural decisions before implementation.
- Report all created and modified files after completing a task.

### 6.2 Documentation and Research

Before implementing unfamiliar technologies or APIs, consult official documentation.

Relevant documentation:

- https://fastapi.tiangolo.com/
- https://docs.python.org/3/
- https://docs.astral.sh/uv/
- https://docs.sqlalchemy.org/
- https://alembic.sqlalchemy.org/
- https://docs.pydantic.dev/
- https://www.sqlite.org/docs.html
- https://www.postgresql.org/docs/

Prefer official documentation over outdated tutorials and unverified implementation examples.

### 6.3 Testing

Testing must accompany implementation.

Use:

- Unit tests for business logic.
- API tests for endpoints.
- Repository tests for data access.
- Database tests for models and migrations.
- Integration tests for important workflows.
- Security tests for validation and authorization where applicable.

Use isolated test databases.

Never run automated tests against the production database.

### 6.4 Code Quality

- Follow PEP 8 conventions.
- Use type hints.
- Prefer small, focused functions.
- Avoid unnecessary global state.
- Use structured exception handling.
- Keep API schemas separate from database models.
- Avoid exposing internal database objects directly through API responses.
- Keep dependencies explicit and managed through uv.
- Run Ruff and relevant type checks.

### 6.5 Git and Commit Policy

Every individual file created or modified must have its own Git commit.

For example, if a task creates three files, it must produce three separate commits.

Commit messages must describe the change in one sentence.

Use Conventional Commits where practical.

Examples:

```text
feat(backend): initialize FastAPI application
feat(backend): add domain blocklist model
feat(backend): implement blocklist retrieval endpoint
test(backend): add blocklist service tests
docs(backend): document database configuration
fix(backend): validate domain normalization
```

Before committing:

1. Review the file changes.
2. Run relevant tests.
3. Run formatting and linting.
4. Verify no secrets or local databases are included.
5. Inspect the commit content.

AI agents must not commit or push changes without the project owner's approval.

### 6.6 Versioning and Releases

Use Semantic Versioning from the initial project foundation.

Format:

`MAJOR.MINOR.PATCH`

Initial development follows the `0.x.y` version series.

Every completed milestone must result in:

1. Reviewed implementation.
2. Passing required tests.
3. Updated documentation.
4. Updated backend package version.
5. Release notes.
6. Git release tag.
7. GitHub release when approved.

Suggested tags:

```text
backend-v0.1.0
backend-v0.2.0
backend-v0.3.0
```

Backend versioning is independent of Android versioning.

## 7. API Design Principles

The backend exposes versioned REST endpoints.

Initial API prefix:

```text
/api/v1/
```

API requirements:

- Use meaningful resource-oriented endpoints.
- Use appropriate HTTP methods and status codes.
- Validate requests and responses using Pydantic.
- Return consistent error structures.
- Document endpoints using OpenAPI.
- Avoid exposing sensitive information.
- Maintain backward compatibility where practical.
- Introduce breaking changes through controlled API versioning.

API contracts must be documented and coordinated with the Android application before integration.

## 8. Development Milestones

# Milestone B0 — Backend Project Foundation

**Target version:** 0.1.0

**Objective:** Initialize the Python backend and establish the development environment.

### Phase B0.1 — Development Environment

- [ ] B0.1.1 — Verify Python installation.
- [ ] B0.1.2 — Establish the supported Python version.
- [ ] B0.1.3 — Verify uv installation.
- [ ] B0.1.4 — Establish the virtual environment.
- [ ] B0.1.5 — Review existing environment configuration without opening private environment files.

### Phase B0.2 — Project Initialization

- [ ] B0.2.1 — Initialize the Python project using uv.
- [ ] B0.2.2 — Configure `pyproject.toml`.
- [ ] B0.2.3 — Create the FastAPI application structure.
- [ ] B0.2.4 — Establish the application entry point.
- [ ] B0.2.5 — Configure dependency management.
- [ ] B0.2.6 — Configure `.gitignore`.
- [ ] B0.2.7 — Review and update `.env.example` if necessary.

### Phase B0.3 — Application Foundation

- [ ] B0.3.1 — Configure application settings.
- [ ] B0.3.2 — Implement the application factory or entry point structure.
- [ ] B0.3.3 — Configure API routing.
- [ ] B0.3.4 — Establish initial exception handling.
- [ ] B0.3.5 — Configure structured logging.
- [ ] B0.3.6 — Add the health-check endpoint.

### Phase B0.4 — Quality Assurance

- [ ] B0.4.1 — Configure Pytest.
- [ ] B0.4.2 — Configure Ruff.
- [ ] B0.4.3 — Add initial application tests.
- [ ] B0.4.4 — Verify the development server.
- [ ] B0.4.5 — Verify OpenAPI documentation.
- [ ] B0.4.6 — Document local development setup.

**Milestone completion criteria:**

The FastAPI application runs locally, has a maintainable project structure, exposes a working health endpoint and passes its initial tests.

**Release:** `backend-v0.1.0`

---

# Milestone B1 — Database Foundation

**Target version:** 0.2.0

**Objective:** Establish database integration and persistence architecture.

### Phase B1.1 — Database Architecture

- [ ] B1.1.1 — Define database configuration strategy.
- [ ] B1.1.2 — Configure SQLAlchemy 2.
- [ ] B1.1.3 — Configure SQLite for local development.
- [ ] B1.1.4 — Establish PostgreSQL compatibility.
- [ ] B1.1.5 — Configure database connection management.

### Phase B1.2 — Database Structure

- [ ] B1.2.1 — Establish the declarative model base.
- [ ] B1.2.2 — Establish UUID primary-key conventions.
- [ ] B1.2.3 — Configure model metadata.
- [ ] B1.2.4 — Configure Alembic.
- [ ] B1.2.5 — Implement initial migration structure.

### Phase B1.3 — Database Operations

- [ ] B1.3.1 — Implement database session management.
- [ ] B1.3.2 — Establish repository conventions.
- [ ] B1.3.3 — Implement transaction management.
- [ ] B1.3.4 — Handle database errors appropriately.

### Phase B1.4 — Testing

- [ ] B1.4.1 — Test SQLite connectivity.
- [ ] B1.4.2 — Test UUID generation and persistence.
- [ ] B1.4.3 — Test model constraints.
- [ ] B1.4.4 — Test migration operations.
- [ ] B1.4.5 — Verify that database configuration is environment-driven.

**Milestone completion criteria:**

The backend supports reliable local persistence using SQLite, has UUID-based database conventions and has a documented path to PostgreSQL production deployment.

**Release:** `backend-v0.2.0`

---

# Milestone B2 — Adult Domain Management

**Target version:** 0.3.0

**Objective:** Establish the backend's core domain filtering data model and business logic.

### Phase B2.1 — Domain Data Design

- [ ] B2.1.1 — Define the adult-domain data model.
- [ ] B2.1.2 — Define domain normalization rules.
- [ ] B2.1.3 — Define domain validation rules.
- [ ] B2.1.4 — Define blocklist categorization and metadata.
- [ ] B2.1.5 — Define domain uniqueness constraints.

### Phase B2.2 — Domain Management Services

- [ ] B2.2.1 — Implement domain repositories.
- [ ] B2.2.2 — Implement domain creation and persistence.
- [ ] B2.2.3 — Implement domain lookup.
- [ ] B2.2.4 — Implement duplicate detection.
- [ ] B2.2.5 — Implement domain update and removal operations.
- [ ] B2.2.6 — Implement bulk domain processing.

### Phase B2.3 — Blocklist Management

- [ ] B2.3.1 — Define blocklist metadata.
- [ ] B2.3.2 — Implement blocklist organization.
- [ ] B2.3.3 — Implement blocklist versioning.
- [ ] B2.3.4 — Define rule publication and update policies.
- [ ] B2.3.5 — Establish initial blocklist data ingestion strategy.

### Phase B2.4 — Testing

- [ ] B2.4.1 — Test domain normalization.
- [ ] B2.4.2 — Test domain validation.
- [ ] B2.4.3 — Test duplicate handling.
- [ ] B2.4.4 — Test database persistence.
- [ ] B2.4.5 — Test blocklist versioning.
- [ ] B2.4.6 — Test invalid input handling.

**Milestone completion criteria:**

The backend can maintain, validate and organize adult-domain filtering data through a tested business logic layer.

**Release:** `backend-v0.3.0`

---

# Milestone B3 — Blocklist REST API

**Target version:** 0.4.0

**Objective:** Expose the domain filtering functionality through a documented REST API.

### Phase B3.1 — API Architecture

- [ ] B3.1.1 — Establish API versioning.
- [ ] B3.1.2 — Define request schemas.
- [ ] B3.1.3 — Define response schemas.
- [ ] B3.1.4 — Define consistent API error responses.
- [ ] B3.1.5 — Document API conventions.

### Phase B3.2 — Blocklist Endpoints

- [ ] B3.2.1 — Implement blocklist listing endpoint.
- [ ] B3.2.2 — Implement blocklist retrieval endpoint.
- [ ] B3.2.3 — Implement blocklist version endpoint.
- [ ] B3.2.4 — Implement pagination or appropriate response-size controls.
- [ ] B3.2.5 — Implement response validation.

### Phase B3.3 — API Reliability

- [ ] B3.3.1 — Implement appropriate HTTP status codes.
- [ ] B3.3.2 — Implement request validation.
- [ ] B3.3.3 — Handle missing resources.
- [ ] B3.3.4 — Handle database errors.
- [ ] B3.3.5 — Review API performance.

### Phase B3.4 — Testing and Documentation

- [ ] B3.4.1 — Test all implemented endpoints.
- [ ] B3.4.2 — Test invalid requests.
- [ ] B3.4.3 — Test empty blocklists.
- [ ] B3.4.4 — Test pagination and response limits.
- [ ] B3.4.5 — Review generated OpenAPI documentation.
- [ ] B3.4.6 — Publish API contracts for Android integration.

**Milestone completion criteria:**

The backend exposes tested, documented endpoints capable of delivering versioned filtering rules to Android clients.

**Release:** `backend-v0.4.0`

---

# Milestone B4 — Blocklist Synchronization Support

**Target version:** 0.5.0

**Objective:** Establish reliable blocklist distribution and synchronization support.

### Phase B4.1 — Synchronization Design

- [ ] B4.1.1 — Define the synchronization protocol.
- [ ] B4.1.2 — Define blocklist version comparison.
- [ ] B4.1.3 — Define update response formats.
- [ ] B4.1.4 — Define integrity validation requirements.
- [ ] B4.1.5 — Define synchronization failure behavior.

### Phase B4.2 — Distribution Services

- [ ] B4.2.1 — Implement published blocklist retrieval.
- [ ] B4.2.2 — Implement version-aware retrieval.
- [ ] B4.2.3 — Implement appropriate response metadata.
- [ ] B4.2.4 — Implement filtering rule integrity metadata.
- [ ] B4.2.5 — Evaluate efficient update delivery.

### Phase B4.3 — Data Management

- [ ] B4.3.1 — Establish blocklist publication workflow.
- [ ] B4.3.2 — Establish data update procedures.
- [ ] B4.3.3 — Establish rollback procedures.
- [ ] B4.3.4 — Document data source management.
- [ ] B4.3.5 — Establish update validation procedures.

### Phase B4.4 — Testing

- [ ] B4.4.1 — Test version comparison.
- [ ] B4.4.2 — Test blocklist delivery.
- [ ] B4.4.3 — Test integrity metadata.
- [ ] B4.4.4 — Test invalid versions.
- [ ] B4.4.5 — Test empty and large blocklists.
- [ ] B4.4.6 — Test synchronization compatibility with Android contracts.

**Milestone completion criteria:**

The backend can distribute validated, versioned blocklists in a format compatible with the Android application.

**Release:** `backend-v0.5.0`

---

# Milestone B5 — Security, Deployment and MVP Readiness

**Target version:** 0.6.0

**Objective:** Prepare the backend for production deployment and integration with the Android MVP.

### Phase B5.1 — Security

- [ ] B5.1.1 — Review API security.
- [ ] B5.1.2 — Review input validation.
- [ ] B5.1.3 — Review database access and permissions.
- [ ] B5.1.4 — Review sensitive information handling.
- [ ] B5.1.5 — Review rate-limiting requirements.
- [ ] B5.1.6 — Review dependency vulnerabilities.

### Phase B5.2 — Production Database

- [ ] B5.2.1 — Validate PostgreSQL compatibility.
- [ ] B5.2.2 — Test production database migrations.
- [ ] B5.2.3 — Verify database connection configuration.
- [ ] B5.2.4 — Review connection pooling.
- [ ] B5.2.5 — Document database backup and recovery considerations.

### Phase B5.3 — Deployment

- [ ] B5.3.1 — Prepare Docker configuration.
- [ ] B5.3.2 — Prepare production application configuration.
- [ ] B5.3.3 — Configure production logging.
- [ ] B5.3.4 — Prepare health-check functionality.
- [ ] B5.3.5 — Document deployment requirements.
- [ ] B5.3.6 — Deploy to the selected hosting platform.
- [ ] B5.3.7 — Verify production API connectivity.

### Phase B5.4 — Integration and Final Testing

- [ ] B5.4.1 — Test Android-backend integration.
- [ ] B5.4.2 — Test production blocklist retrieval.
- [ ] B5.4.3 — Test synchronization failure scenarios.
- [ ] B5.4.4 — Perform API regression testing.
- [ ] B5.4.5 — Review production configuration.
- [ ] B5.4.6 — Prepare release documentation.

**Milestone completion criteria:**

The backend supports the Android MVP, operates with PostgreSQL in production, exposes documented and tested APIs, and is ready for deployment and continued operation.

**Release:** `backend-v0.6.0`

---

## 9. Future Development

Future milestones may include:

- Advanced domain intelligence.
- Automated blocklist ingestion and validation.
- Content-classification services.
- AI model management.
- On-device model distribution.
- Advanced analytics.
- Optional user accounts and device synchronization.

These features require separate product approval and planning.

They must not be introduced into the MVP without explicit authorization.

## 10. Milestone Completion and Release Procedure

A milestone is complete only when:

1. All approved tasks have been implemented.
2. Required automated tests pass.
3. Code quality checks pass.
4. Database migrations have been verified where applicable.
5. API documentation is updated.
6. Individual file commits have been reviewed.
7. No unresolved critical issues remain.
8. The project owner approves completion.

After approval:

- Update the backend package version.
- Prepare release notes.
- Create the appropriate Git tag.
- Publish the GitHub release when approved.

Production deployment is a separate operation and must not happen automatically as a consequence of creating a release.

## 11. Task Execution Protocol

For every task, follow this process:

1. Read the assigned task.
2. Inspect existing implementation and documentation.
3. Consult relevant official documentation.
4. Present the proposed implementation.
5. Wait for project-owner approval.
6. Implement only the approved task.
7. Write and execute relevant tests.
8. Run formatting, linting and type checks.
9. Review database and API compatibility.
10. Create one individual commit per created or modified file.
11. Report completed work, test results and commit hashes.
12. Wait for the next task assignment.

### Environment File Protection

This rule applies throughout all development milestones:

**NEVER modify `.env.local` or `.env.production`.**

Agents may update `.env.example` as new configuration requirements are introduced.

Never print, expose or commit production secrets.

---

**ClearGuard Backend Development**  
*Reliable filtering intelligence, built one task at a time.*