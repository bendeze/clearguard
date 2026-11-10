# ClearGuard Android Integration — REST API Contract

**Target Version:** Milestone B3 (`v0.4.0`)  
**Base Path:** `/api/v1`  
**Communication Protocol:** HTTPS / JSON  
**Encoding:** UTF-8  

---

## 1. Overview & Architecture

The ClearGuard backend provides versioned adult domain blocklists to the ClearGuard Android application. The Android client operates **offline-first**: filtering decisions are made locally on the device (via local VPN or private DNS filtering). The backend is queried only during synchronization cycles to detect updates and retrieve modified domain lists.

---

## 2. Synchronization Protocol

Android clients should schedule background sync jobs (e.g. using `WorkManager` with `NetworkType.CONNECTED` or `UNMETERED` constraints):

```text
[ Android Device ]                                [ Backend API ]
        |                                                |
        |--- 1. GET /api/v1/blocklists/{id}/versions/latest --->|
        |<-- Returns { version, content_hash, ... } -----|
        |                                                |
        |-- Check: local_hash == content_hash ?          |
        |   ├── YES: Up-to-date (Stop sync, battery saved)|
        |   └── NO: Proceed to Step 2                     |
        |                                                |
        |--- 2. GET /api/v1/blocklists/{id}/domains?limit=1000 ->|
        |<-- Returns Paginated Domains List -------------|
        |    (Repeat for next pages until has_more=false)|
        |                                                |
        |--- 3. Local Verification ----------------------|
        |    Sort downloaded domain names alphabetically |
        |    Compute SHA-256 over newline-delimited list |
        |    Verify SHA-256 == content_hash              |
        |    If verified: Replace local SQLite / Room DB |
        |    Update stored local_hash and version        |
```

---

## 3. Endpoints Specification

### 3.1 Get Latest Blocklist Release Version

Retrieves the latest published snapshot metadata, including the cryptographic SHA-256 hash.

- **Method:** `GET`
- **Path:** `/api/v1/blocklists/{blocklist_id}/versions/latest`
- **Headers:** `Accept: application/json`

#### Response (`200 OK`)

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "blocklist_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "version": "1.0.4",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "domain_count": 42150,
  "changelog": "Added high-confidence adult advertising domains",
  "created_at": "2026-11-10T08:00:00Z"
}
```

---

### 3.2 Download Blocklist Domains (Paginated)

Retrieves active filtering domains associated with the blocklist.

- **Method:** `GET`
- **Path:** `/api/v1/blocklists/{blocklist_id}/domains?offset={offset}&limit={limit}`
- **Query Parameters:**
  - `offset` *(optional integer, default: 0, ge: 0)*: Zero-based item offset.
  - `limit` *(optional integer, default: 50, ge: 1, le: 1000)*: Max items per page.

#### Response (`200 OK`)

```json
{
  "items": [
    {
      "id": "80c4b223-d503-4468-9e81-4f200018f8aa",
      "domain": "bad-adult-domain.com",
      "category": "pornography",
      "status": "active",
      "confidence_score": 1.0,
      "source": "curated_feed",
      "notes": null,
      "created_at": "2026-11-10T07:30:00Z",
      "updated_at": "2026-11-10T07:30:00Z"
    }
  ],
  "total": 42150,
  "offset": 0,
  "limit": 1000,
  "has_more": true
}
```

---

### 3.3 List Registered Blocklists

Retrieves all available blocklist categories (useful for user settings).

- **Method:** `GET`
- **Path:** `/api/v1/blocklists?offset=0&limit=50`

#### Response (`200 OK`)

```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Default Pornography Filter",
      "description": "System-wide high-confidence adult content protection list",
      "is_default": true,
      "is_active": true,
      "current_version": "1.0.4",
      "domain_count": 42150,
      "created_at": "2026-11-08T12:00:00Z",
      "updated_at": "2026-11-10T08:00:00Z"
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 50,
  "has_more": false
}
```

---

## 4. Error Structure

All error responses return standard HTTP status codes accompanied by the uniform error envelope:

```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Blocklist with identifier '...' was not found.",
    "details": {
      "entity": "Blocklist",
      "id": "..."
    }
  }
}
```

### Common Error Codes for Android Handling

| Code | HTTP Status | Recommended Action |
|---|---|---|
| `ENTITY_NOT_FOUND` | 404 | Query default blocklist instead or notify user |
| `REQUEST_VALIDATION_ERROR` | 422 | Check query parameters / UUID formatting |
| `INTERNAL_SERVER_ERROR` | 500 | Retry later using exponential backoff |

---

## 5. Recommended Android Kotlin Data Models

Android clients using `kotlinx.serialization` can model responses as follows:

```kotlin
package com.clearguard.network.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class BlocklistVersionResponse(
    val id: String,
    @SerialName("blocklist_id") val blocklistId: String,
    val version: String,
    @SerialName("content_hash") val contentHash: String,
    @SerialName("domain_count") val domainCount: Int,
    val changelog: String? = null,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class DomainItem(
    val id: String,
    val domain: String,
    val category: String,
    val status: String,
    @SerialName("confidence_score") val confidenceScore: Double
)

@Serializable
data class BlocklistDomainsResponse(
    val items: List<DomainItem>,
    val total: Int,
    val offset: Int,
    val limit: Int,
    @SerialName("has_more") val hasMore: Boolean
)

@Serializable
data class ApiErrorEnvelope(
    val error: ApiErrorDetail
)

@Serializable
data class ApiErrorDetail(
    val code: String,
    val message: String
)
```

