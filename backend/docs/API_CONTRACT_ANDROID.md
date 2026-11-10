# ClearGuard Android Integration — REST API Contract

**Target Version:** Milestone B4 (`v0.5.0`)  
**Base Path:** `/api/v1`  
**Communication Protocol:** HTTPS / JSON & Raw UTF-8 Text Streams  
**Encoding:** UTF-8  

---

## 1. Overview & Architecture

The ClearGuard backend provides versioned adult domain blocklists to the ClearGuard Android application. The Android client operates **offline-first**: filtering decisions are made locally on the device (via local VPN or private DNS filtering). The backend is queried during scheduled synchronization cycles to evaluate updates, check cryptographic integrity, and download modified rule lists.

---

## 2. Recommended Synchronization Protocol (Battery & Bandwidth Optimized)

Android clients should schedule background sync jobs (e.g. using `WorkManager` with `NetworkType.CONNECTED` or `UNMETERED` constraints):

```text
[ Android Device ]                                [ Backend API ]
        |                                                |
        |--- 1. POST /api/v1/sync/batch ---------------->|
        |    Payload: [{ blocklist_id, version, hash }]  |
        |<-- Returns [{ status, update_required, ... }] -|
        |                                                |
        |-- For each blocklist:                          |
        |   ├── UP_TO_DATE: Skip (Zero bandwidth used)  |
        |   └── UPDATE_AVAILABLE / OUTDATED: Step 2      |
        |                                                |
        |--- 2. GET /api/v1/sync/blocklists/{id}/download|
        |    Headers: If-None-Match: "<cached_hash>"     |
        |    Query: format=raw                           |
        |                                                |
        |<-- Returns 304 Not Modified (If match) --------|
        |<-- OR Returns 200 OK with newline stream ------|
        |                                                |
        |--- 3. Local Verification & Atomic Commit ------|
        |    Compute SHA-256 over raw downloaded bytes   |
        |    Verify SHA-256 == X-Content-Hash header     |
        |    If verified: Replace local SQLite Room DB   |
        |    Update stored local_hash and version        |
```

---

## 3. Endpoints Specification

### 3.1 Batch Synchronization Check (`POST /api/v1/sync/batch`)

Evaluates synchronization status for all subscribed blocklists in a single HTTP request.

- **Method:** `POST`
- **Path:** `/api/v1/sync/batch`
- **Headers:** `Content-Type: application/json`, `Accept: application/json`

#### Request Payload
```json
{
  "items": [
    {
      "blocklist_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "client_version": "1.0.0",
      "client_content_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
    }
  ]
}
```

#### Response (`200 OK`)
```json
{
  "items": [
    {
      "blocklist_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "status": "update_available",
      "update_required": true,
      "latest_version": "1.1.0",
      "latest_content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "domain_count": 42150,
      "changelog": "Added new malicious domains",
      "download_url": "/api/v1/sync/blocklists/3fa85f64-5717-4562-b3fc-2c963f66afa6/download"
    }
  ]
}
```

---

### 3.2 Single Synchronization Check (`POST /api/v1/sync/check`)

Evaluates synchronization status for an individual blocklist.

- **Method:** `POST`
- **Path:** `/api/v1/sync/check`
- **Payload:** Same as a single item in the batch request.
- **Response:** Single item from `SyncCheckResponse`.

---

### 3.3 Download Blocklist Filtering Rules (`GET /api/v1/sync/blocklists/{id}/download`)

Downloads active filtering domains in raw newline-delimited text or structured JSON, supporting HTTP conditional caching.

- **Method:** `GET`
- **Path:** `/api/v1/sync/blocklists/{blocklist_id}/download`
- **Query Parameters:**
  - `format` *(optional string: `"raw"` or `"json"`, default: `"json"`)*: Format of the response payload.
  - `version` *(optional string)*: Specific release version to download. Defaults to active release.
- **Request Headers:**
  - `If-None-Match`: Client cached ETag / content hash (e.g. `"<content_hash>"`).
  - `Accept`: `text/plain` or `application/json`.

#### Response (`304 Not Modified`)
Returned when the client's `If-None-Match` matches the active server release. The response body is empty (`0 bytes`), saving mobile bandwidth.

#### Response (`200 OK` — `format=raw` or `Accept: text/plain`)
- **Headers:**
  - `Content-Type: text/plain; charset=utf-8`
  - `ETag: "<content_hash>"`
  - `X-Content-Hash: <sha256_hex>`
  - `X-Blocklist-Version: 1.1.0`
  - `X-Domain-Count: 42150`
  - `Cache-Control: public, max-age=3600`
- **Body:**
```text
bad-domain.com
malicious-adult.net
xxx-tracker.org
```

#### Response (`200 OK` — `format=json`)
```json
{
  "blocklist_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Default Adult Filter",
  "version": "1.1.0",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "domain_count": 42150,
  "published_at": "2026-11-10T12:00:00Z",
  "changelog": "Added new malicious domains",
  "domains": [
    "bad-domain.com",
    "malicious-adult.net",
    "xxx-tracker.org"
  ]
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

---

## 5. Recommended Android Kotlin Models & Retrofit Interface

```kotlin
package com.clearguard.network.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming

@Serializable
enum class SyncStatus {
    @SerialName("up_to_date") UP_TO_DATE,
    @SerialName("update_available") UPDATE_AVAILABLE,
    @SerialName("outdated") OUTDATED
}

@Serializable
data class SyncCheckItem(
    @SerialName("blocklist_id") val blocklistId: String,
    @SerialName("client_version") val clientVersion: String? = null,
    @SerialName("client_content_hash") val clientContentHash: String? = null
)

@Serializable
data class SyncCheckResponse(
    @SerialName("blocklist_id") val blocklistId: String,
    val status: SyncStatus,
    @SerialName("update_required") val updateRequired: Boolean,
    @SerialName("latest_version") val latestVersion: String,
    @SerialName("latest_content_hash") val latestContentHash: String,
    @SerialName("domain_count") val domainCount: Int,
    val changelog: String? = null,
    @SerialName("download_url") val downloadUrl: String
)

@Serializable
data class SyncBatchCheckRequest(
    val items: List<SyncCheckItem>
)

@Serializable
data class SyncBatchCheckResponse(
    val items: List<SyncCheckResponse>
)

@Serializable
data class BlocklistDownloadResponse(
    @SerialName("blocklist_id") val blocklistId: String,
    val name: String,
    val version: String,
    @SerialName("content_hash") val contentHash: String,
    @SerialName("domain_count") val domainCount: Int,
    @SerialName("published_at") val publishedAt: String,
    val changelog: String? = null,
    val domains: List<String>
)

interface ClearGuardSyncApi {
    @POST("api/v1/sync/batch")
    async suspend fun batchCheckUpdates(@Body request: SyncBatchCheckRequest): SyncBatchCheckResponse

    @POST("api/v1/sync/check")
    async suspend fun checkUpdate(@Body item: SyncCheckItem): SyncCheckResponse

    @Streaming
    @GET("api/v1/sync/blocklists/{id}/download")
    async suspend fun downloadRawRules(
        @Path("id") blocklistId: String,
        @Query("format") format: String = "raw",
        @Header("If-None-Match") ifNoneMatch: String? = null
    ): Response<ResponseBody>
}
```
