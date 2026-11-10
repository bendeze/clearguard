# ClearGuard Blocklist Synchronization Protocol Specification

**Document Version:** 1.0.0  
**Target Milestone:** Milestone B4  
**Applies to:** Android Client (`ClearGuard-Android`) & Backend API (`ClearGuard-Backend`)

---

## 1. Architectural Philosophy

ClearGuard adheres strictly to an **offline-first** filtering model:
1. **Zero-Latency Network Filtering**: DNS queries and VPN network interceptions are evaluated entirely against an on-device local database (Room / SQLite). The device never performs real-time cloud lookups during web browsing.
2. **Periodic Delta & Snapshot Synchronization**: Filtering rules are updated asynchronously via periodic background synchronization jobs managed by Android's `WorkManager`.
3. **Resource Conservation**: Handshakes minimize network payload size and battery drain by verifying content hashes before downloading rule datasets.

---

## 2. Synchronization State Machine

```text
                  [ Start Sync Cycle ]
                           |
                           v
              [ Query Sync Check Endpoint ]
                           |
            +--------------+--------------+
            |                             |
      (Hash Matches)                (Hash Differs)
            |                             |
            v                             v
      [ UP_TO_DATE ]            Check Semver Order
    (No action needed;         +----------+----------+
     battery preserved)        |                     |
                        (Client < Latest)     (Diverged / No Version)
                               |                     |
                               v                     v
                      [ UPDATE_AVAILABLE ]      [ OUTDATED ]
                               |                     |
                               +----------+----------+
                                          |
                                          v
                              [ Download Domain List ]
                                          |
                                          v
                              [ Verify SHA-256 Hash ]
                                          |
                               +----------+----------+
                               |                     |
                          (Valid Hash)         (Hash Mismatch)
                               |                     |
                               v                     v
                     [ Commit to Local DB ]   [ Discard Payload ]
                     [ Update Stored Hash ]   [ Log Warning ]
                                              [ Keep Existing DB ]
```

---

## 3. Cryptographic Integrity Standard

Every published blocklist version computes an immutable cryptographic hash over its active domain members:

- **Algorithm:** `SHA-256`
- **Normalization:**
  1. Each domain name is lowercased and stripped of whitespace and trailing dots.
  2. The list of active domain names is sorted in ascending alphabetical order (`A-Z`).
  3. Domain names are joined by a single Unix newline character (`\n`).
  4. There is no trailing newline after the last domain.
- **Encoding:** `UTF-8`
- **Output:** Hex-encoded 64-character lowercase string (e.g. `a1b2c3d4...`).

### Integrity Verification on Android
Before committing a downloaded list of domains into the on-device database:
1. The client sorts the received domain strings alphabetically.
2. The client calculates the SHA-256 digest over the newline-delimited strings.
3. The client verifies that `computed_sha256 == latest_content_hash`.
4. If the digests match, the local database transaction commits. If not, the transaction aborts and rolls back.

---

## 4. Synchronization Handshake Endpoints

### 4.1 Single Blocklist Sync Check

- **Method:** `POST /api/v1/sync/check` (or `GET /api/v1/blocklists/{id}/versions/latest`)
- **Request Body:**
  ```json
  {
    "blocklist_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "client_version": "1.0.0",
    "client_content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
  ```
- **Response Body (`200 OK`):**
  ```json
  {
    "blocklist_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "update_available",
    "update_required": true,
    "latest_version": "1.0.1",
    "latest_content_hash": "d4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35",
    "domain_count": 42500,
    "changelog": "Added 350 newly discovered explicit domains",
    "download_url": "/api/v1/blocklists/3fa85f64-5717-4562-b3fc-2c963f66afa6/domains"
  }
  ```

### 4.2 Batch Sync Check

Supports querying all active on-device categories (e.g., standard adult, gambling, explicit video) in a single HTTP request:

- **Method:** `POST /api/v1/sync/batch`
- **Request Body:**
  ```json
  {
    "items": [
      {
        "blocklist_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "client_version": "1.0.0",
        "client_content_hash": "e3b0c44..."
      },
      {
        "blocklist_id": "80c4b223-d503-4468-9e81-4f200018f8aa",
        "client_version": "2.1.0",
        "client_content_hash": "a1b2c3d..."
      }
    ]
  }
  ```

---

## 5. Failure Handling & Resilience Policies

| Failure Condition | Client Action | Fallback Strategy |
|---|---|---|
| **Hash Mismatch** | Downloaded data digest does not match `latest_content_hash`. | Discard downloaded data, log error, retain existing local database, retry in next sync cycle. |
| **Network Timeout / Drop** | Connection interrupted mid-download. | Abort transaction, continue using local database (protection remains 100% active). |
| **HTTP 5xx Server Error** | Backend temporarily unavailable. | Exponential backoff (retry after 15m, 1h, 6h). Protection remains active. |
| **HTTP 404 Blocklist Deleted** | Blocklist collection was retired or removed on backend. | Mark blocklist as disabled or fallback to default core blocklist. |
| **HTTP 422 Validation Error** | Request payload rejected due to malformed UUID or schema. | Log client bug report, abort sync until next application update. |

