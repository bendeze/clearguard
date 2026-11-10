# ClearGuard Blocklist Data Management Runbook & Procedures

**Document Version:** 1.0.0  
**Target Milestone:** B4 (Blocklist Synchronization Support)  
**Applicability:** Backend Data Operations, CI/CD Automated Pipelines, and Emergency Administration

---

## 1. Overview & Lifecycle

Blocklists in ClearGuard represent curated, immutable release snapshots of adult and sensitive domain names used by Android client devices to perform local DNS filtering.

The data management pipeline follows a strict seven-stage lifecycle:

```text
[External Feeds]
       │
       ▼
1. INGESTION  ─── (Hosts, Adblock, Plain syntax parsing)
       │
       ▼
2. VALIDATION ─── (RFC 1035/1123, IDN Punycode, strip scheme/port/path)
       │
       ▼
3. DEDUPLICATION & PERSISTENCE ─── (Global unique domain table)
       │
       ▼
4. ASSOCIATION ─── (Link active domain records to target Blocklist)
       │
       ▼
5. SAFETY AUDIT ─── (Anomalous drop check, zero-domain protection)
       │
       ▼
6. PUBLICATION ─── (SHA-256 hash generation, immutable snapshot creation)
       │
       ▼
7. DISTRIBUTION & ROLLBACK ─── (Cached HTTP delivery, version reversion)
```

---

## 2. Supported Data Feeds & Parsing Syntax

ClearGuard natively ingests feeds in three canonical formats via `/api/v1/blocklists/{id}/ingest`:

1. **Hosts Format**:
   - Lines formatted as `0.0.0.0 domain.com` or `127.0.0.1 domain.com`.
   - Supports inline and line comments starting with `#`.
2. **Adblock Plus / Brave Syntax**:
   - Lines formatted as `||domain.com^`.
   - Strips leading `||` and trailing `^` or `^$important`.
3. **Plain Text Format**:
   - Single fully-qualified domain name per line.
   - Blank lines and whitespace are automatically pruned.

---

## 3. Pre-Publication Safety Guardrails

To prevent accidental wipeouts or corrupted releases from reaching millions of mobile devices, the `BlocklistService.publish_version` routine enforces automated safety validations:

1. **Zero-Domain Protection**:
   - If a blocklist previously contained active domains, attempting to publish a release snapshot containing 0 domains is immediately rejected with HTTP 422 (`ValidationError`).
2. **Anomalous Drop Prevention (>50% reduction)**:
   - If the new active domain count represents more than a 50% drop compared to the previous release (e.g. dropping from 100,000 domains to 30,000 domains due to a broken upstream crawler), publication is blocked with HTTP 422.
3. **Emergency Override (`force=true`)**:
   - When intentional deprecations or major reorganizations require publishing a significantly smaller snapshot, the administrative caller must explicitly pass `"force": true` in the `BlocklistPublishRequest` payload.

---

## 4. Emergency Rollback Procedures (SOP)

If a bad upstream feed introduces false positives or blocking bugs, operators can immediately revert the active blocklist release pointer without data loss.

### 4.1 Rollback API Invocation
An operator or automated incident response system issues a POST request to:

```http
POST /api/v1/blocklists/{blocklist_id}/rollback
Content-Type: application/json

{
  "target_version": "1.0.0",
  "reason": "False positives detected in release 1.1.0 on critical CDN domains"
}
```

### 4.2 Architectural Impact
1. The `Blocklist.current_version` pointer is updated to `"1.0.0"`.
2. The `Blocklist.domain_count` is updated to the snapshot's recorded count.
3. Historical snapshots are **never deleted**, preserving full cryptographic and audit traceability.
4. Subsequent calls to:
   - `GET /api/v1/sync/blocklists/{id}/latest` return snapshot `1.0.0`.
   - `GET /api/v1/sync/blocklists/{id}/download` serve snapshot `1.0.0` content and ETag.
   - `POST /api/v1/sync/check` reports that clients on `1.1.0` have an `outdated` or `update_available` release, directing them to download the known-good `1.0.0` snapshot.

---

## 5. Client Synchronization Recovery Guarantee

When a rollback occurs:
- Android devices during periodic background sync compare their stored content hash and version against `/api/v1/sync/check`.
- Because the active server hash reverts to the `1.0.0` snapshot hash, client hash mismatch triggers `SyncStatus.OUTDATED`.
- The Android client downloads the `1.0.0` payload, validates the SHA-256 integrity hash, and atomically replaces its on-device SQLite filtering tables.

