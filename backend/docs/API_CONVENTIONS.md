# ClearGuard API Architecture & Conventions

**Document Version:** 1.0.0  
**Target API Version:** `v1` (`/api/v1`)  
**Status:** Canonical REST Specification

---

## 1. Overview & Architectural Principles

The ClearGuard API provides client synchronization, blocklist distribution, and domain intelligence management for the ClearGuard Android application and administration tooling.

Key architectural principles:
- **Offline-First Support**: Android devices maintain local filtering rules. API endpoints prioritize deterministic version snapshots, caching headers, and cryptographic integrity hashes to support efficient client updates without requiring continuous connectivity.
- **RESTful Resource Hierarchy**: Resources use plural nouns and standard HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`).
- **Consistent Envelope Models**: Collections adhere to uniform pagination contracts, and exceptions map to standard error payloads.
- **Strict Pydantic Validation**: All requests and responses are strongly typed and validated against explicit Pydantic schemas.

---

## 2. API Versioning & URL Structure

The API is explicitly versioned in the URL path.

- **Base URL Prefix**: `/api/v1`
- **Root Status Probe**: `GET /` (returns service metadata, current version, documentation links)
- **Health Check**: `GET /api/v1/health` (system readiness and database connectivity probe)

### Resource Routes Convention

| Resource Area | Path | Description |
|---|---|---|
| **Blocklists** | `/api/v1/blocklists` | Manage filtering blocklist collections |
| **Blocklist Detail** | `/api/v1/blocklists/{id}` | Inspect or update a specific blocklist |
| **Blocklist Domains** | `/api/v1/blocklists/{id}/domains` | Query or modify domains associated with a blocklist |
| **Blocklist Versions** | `/api/v1/blocklists/{id}/versions` | List historical releases and snapshots |
| **Latest Version** | `/api/v1/blocklists/{id}/versions/latest` | Retrieve current release with SHA-256 hash |
| **Feed Ingestion** | `/api/v1/blocklists/{id}/ingest` | Parse and ingest third-party blocklist feeds |
| **Version Publication** | `/api/v1/blocklists/{id}/publish` | Create and release an immutable version snapshot |

---

## 3. HTTP Methods & Status Codes

ClearGuard strictly adheres to standard HTTP status codes:

| HTTP Verb | Path Type | Success Code | Semantic Meaning |
|---|---|---|---|
| `GET` | Collection / Item | `200 OK` | Resource successfully retrieved |
| `POST` | Collection | `201 Created` | New resource created (`Location` header where applicable) |
| `POST` | Action / Process | `200 OK` | Operation executed (e.g. feed ingestion, publish) |
| `PUT` | Single Resource | `200 OK` | Resource updated |
| `DELETE` | Single Resource | `204 No Content` | Resource deleted (no response body) |

### Error Status Codes

| Status Code | Description | Trigger |
|---|---|---|
| `400 Bad Request` | Malformed Request | Unparseable body, invalid query parameter format |
| `404 Not Found` | Resource Missing | Non-existent blocklist or domain ID |
| `409 Conflict` | Duplicate Resource | Name collision (e.g. blocklist name already taken) |
| `422 Unprocessable Content` | Validation Failure | Pydantic schema violation or RFC 1035/1123 domain failure |
| `500 Internal Server Error` | Server Exception | Uncaught exception (sanitized, internal details redacted) |

---

## 4. Pagination Standard

Collections supporting pagination accept the standard query parameters:

- `offset` *(integer, default: 0, ge: 0)*: Number of items to skip.
- `limit` *(integer, default: 50, ge: 1, le: 1000)*: Maximum items to return.

### Standard Response Envelope (`PaginatedResponse[T]`)

```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Default Pornography Blocklist",
      "is_default": true,
      "domain_count": 42000,
      "current_version": "1.0.4"
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 50,
  "has_more": false
}
```

---

## 5. Standard Error Envelope

All API errors return a standard `ErrorResponse` envelope:

```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Blocklist with identifier '3fa85f64-...' was not found.",
    "details": {
      "entity": "Blocklist",
      "id": "3fa85f64-..."
    }
  }
}
```

Common error codes:
- `ENTITY_NOT_FOUND`: Database entity does not exist.
- `DUPLICATE_ENTITY`: Unique constraint violation.
- `INVALID_DOMAIN`: RFC 1035/1123 validation or normalization error.
- `REQUEST_VALIDATION_ERROR`: Pydantic field constraint violation.
- `DATABASE_CONSTRAINT_ERROR`: Check or foreign key constraint violation.
- `INTERNAL_SERVER_ERROR`: Internal unhandled server error.

---

## 6. Android Client Synchronization Protocol

To ensure minimal battery and bandwidth consumption for Android clients:

1. **Version Check**: The Android client queries `GET /api/v1/blocklists/{id}/versions/latest`.
2. **Integrity Validation**:
   - The response includes `content_hash` (a deterministic SHA-256 of all active domain names sorted alphabetically and newline-delimited).
   - If the local client's hash matches `content_hash`, no download is necessary.
3. **Delta / Full Download**:
   - If the client's version is outdated, it downloads the active domain dataset.
   - The client verifies the local downloaded content against `content_hash` before replacing local SQLite filtering rules.
4. **Conditional Requests**:
   - Release endpoints support standard HTTP `ETag` headers derived from `content_hash`.
   - Android clients supply `If-None-Match: "<content_hash>"`, receiving `304 Not Modified` when rules have not changed.

