"""Version comparison, semantic version parsing, and cryptographic hash verification."""

import hashlib
import hmac
import re
from collections.abc import Sequence

from app.schemas.sync import SyncStatus


def parse_semver(version_str: str | None) -> tuple[int, ...]:
    """Parse a semantic version string into a numeric tuple (major, minor, patch) for comparison."""
    if not version_str or not isinstance(version_str, str):
        return (0, 0, 0)

    # Strip leading 'v' or 'V'
    cleaned = version_str.strip().lstrip("vV")

    # Strip pre-release and build metadata (e.g., -beta.1, +build.123)
    core = re.split(r"[-+]", cleaned, maxsplit=1)[0]

    # Split major, minor, patch and extract leading digits
    parts = core.split(".")
    parsed: list[int] = []
    for part in parts[:3]:
        match = re.match(r"^(\d+)", part)
        if match:
            parsed.append(int(match.group(1)))
        else:
            break

    # Guarantee exactly 3 parts (major, minor, patch)
    while len(parsed) < 3:
        parsed.append(0)

    return tuple(parsed[:3])


def compare_versions(client_version: str | None, latest_version: str) -> int:
    """Compare a client's version against the latest release version.

    Returns:
        -1 if client_version is older than latest_version.
         0 if client_version is equal to latest_version.
         1 if client_version is newer than latest_version.
    """
    if not client_version:
        return -1

    if client_version.strip() == latest_version.strip():
        return 0

    client_parts = parse_semver(client_version)
    latest_parts = parse_semver(latest_version)

    if client_parts < latest_parts:
        return -1
    elif client_parts > latest_parts:
        return 1
    return 0


def determine_sync_status(
    client_version: str | None,
    client_hash: str | None,
    latest_version: str,
    latest_hash: str,
) -> tuple[SyncStatus, bool]:
    """Evaluate client sync status and whether an update is required.

    Returns:
        tuple[SyncStatus, bool]: (status, update_required)
    """
    # 1. If hashes match exactly, client is 100% up to date regardless of version label
    if client_hash and hmac.compare_digest(
        client_hash.strip().lower(), latest_hash.strip().lower()
    ):
        return (SyncStatus.UP_TO_DATE, False)

    # 2. If client has no version or hash provided, it is completely outdated
    if not client_version or not client_hash:
        return (SyncStatus.OUTDATED, True)

    # 3. If version strings match but hashes diverge, content is modified/diverged
    if client_version.strip() == latest_version.strip():
        return (SyncStatus.OUTDATED, True)

    # 4. Check semver order
    cmp_result = compare_versions(client_version, latest_version)
    if cmp_result < 0:
        return (SyncStatus.UPDATE_AVAILABLE, True)

    # Client claims a higher version but hash doesn't match latest
    return (SyncStatus.OUTDATED, True)


def compute_domain_list_hash(domains: Sequence[str]) -> str:
    """Compute deterministic SHA-256 hash of a domain collection.

    Domains are sorted alphabetically, stripped, converted to lowercase,
    and joined with newline characters.
    """
    clean_domains = sorted([d.strip().lower() for d in domains if d and d.strip()])
    payload = "\n".join(clean_domains).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_content_integrity(domains: Sequence[str], expected_hash: str) -> bool:
    """Verify that a collection of domains matches the expected SHA-256 hash."""
    if not expected_hash:
        return False
    computed = compute_domain_list_hash(domains)
    return hmac.compare_digest(computed.lower(), expected_hash.strip().lower())
