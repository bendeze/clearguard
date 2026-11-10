# ClearGuard Backend — Security Audit & Hardening Report

**Document Version:** 1.0.0  
**Target Milestone:** B5 (Security, Deployment and MVP Readiness)  
**Security Baseline:** OWASP API Security Top 10 Compliance Review  

---

## 1. Executive Summary

This security audit reviews the ClearGuard backend against common threat vectors and establishes automated defensive controls prior to production deployment.

Key security controls implemented:
- **Defensive HTTP Headers Middleware**: Protects against clickjacking, MIME sniffing, and downgrade attacks.
- **Configurable CORS Governance**: Restricts browser and cross-origin resource requests.
- **Sliding-Window Rate Limiting**: Mitigates automated scraping and DDoS abuse on bandwidth-heavy distribution endpoints.
- **Strict Parameterized Queries**: Zero raw SQL concatenation throughout ORM and repository layers.
- **Information Leakage Prevention**: Sanitized error envelopes and database URL credential masking.

---

## 2. Threat Modeling & Defensive Controls

### 2.1 Threat Vectors & Mitigations

| Threat Vector | Severity | Mitigation Strategy | Status |
|---|---|---|---|
| **SQL Injection** | Critical | 100% SQLAlchemy 2 parameterized queries; no raw string interpolation in SQL statements. | Verified |
| **Sequential ID Enumeration** | Medium | UUIDv4 identifiers across all entities (`Blocklist`, `Domain`, `BlocklistVersion`). | Verified |
| **Abuse / Denial of Service** | High | Sliding-window IP rate limiter (120 req/min general, 30 req/min download). | Implemented |
| **MIME Sniffing & Clickjacking** | Medium | Automated headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`. | Implemented |
| **Credential / Stack Leakage** | High | Global error handlers mask unhandled exception traces; DB password masking on `Settings`. | Implemented |
| **Cross-Origin Abuse** | Medium | Configurable `cors_origins` whitelist managed via environment variables. | Implemented |
| **Cellular Bandwidth Exhaustion** | High | Conditional HTTP caching via `ETag` and `If-None-Match` (304 Not Modified, 0 bytes). | Implemented |

---

## 3. Database Permission Architecture (PostgreSQL Production)

For production deployments, the database role used by the FastAPI backend runtime must follow the **Principle of Least Privilege**:

### 3.1 Role Separation

1. **Application Runtime Role (`clearguard_app`)**:
   - Capabilities: `SELECT, INSERT, UPDATE, DELETE` on tables and `USAGE, SELECT` on sequences.
   - Forbidden: `CREATE TABLE`, `DROP TABLE`, `ALTER TABLE`, `SUPERUSER`.
   - Cannot perform schema modifications.

2. **Migration Role (`clearguard_migrator`)**:
   - Used exclusively during CI/CD deployment jobs to execute `alembic upgrade head`.
   - Capabilities: DDL operations (`CREATE`, `ALTER`, `DROP`).

---

## 4. Input Validation & Data Boundary Audit

1. **RFC 1035 / RFC 1123 Domain Validation**:
   - Fully enforced in `app/services/domain_validator.py`.
   - Rejects oversized labels (>63 chars), oversized domain strings (>253 chars), consecutive dots, and IP address literals.
2. **Pydantic v2 Schema Enforcement**:
   - `extra="forbid"` on mutation and check request payloads prevents attribute injection.
   - String boundaries (`max_length`, `min_length`, regex patterns) enforced on all incoming strings.

---

## 5. Information Sanitization & Secrets Management

1. **Database URL Masking**:
   - `Settings.masked_database_url` replaces passwords with `***` whenever logged or inspected.
2. **Environment File Quarantine**:
   - `.env.local` and `.env.production` are strictly excluded from source control via `.gitignore`.
3. **Trace Sanitization**:
   - In production (`app_env="production"`), all 500 errors return a sanitized JSON envelope without exposing Python tracebacks or database dialect errors.

