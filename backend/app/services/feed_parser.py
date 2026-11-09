"""Feed parser engine supporting Hosts, plain domain lists, and Adblock syntax."""

import re

from app.core.exceptions import InvalidDomainError
from app.services.domain_validator import normalize_domain, validate_domain

# Common local and loopback hostnames ignored during ingestion
IGNORED_HOSTNAMES: set[str] = {
    "localhost",
    "localhost.localdomain",
    "broadcasthost",
    "local",
    "localdomain",
    "0.0.0.0",
    "127.0.0.1",
    "::1",
}

# Regex to detect hosts file format (IP address followed by whitespace and domain)
HOSTS_LINE_REGEX = re.compile(r"^(?:0\.0\.0\.0|127\.0\.0\.1|::1)\s+([^\s#]+)", re.IGNORECASE)

# Regex to detect Adblock syntax (e.g., ||example.com^ or ||example.com^)
ADBLOCK_REGEX = re.compile(r"^\|\|([a-zA-Z0-9+.-]+)\^?", re.IGNORECASE)


def parse_blocklist_feed(content: str) -> list[str]:
    """Parse raw blocklist feed content in Hosts, plain domain, or Adblock syntax.

    Returns a deduplicated list of valid, normalized domain strings.
    """
    if not content or not isinstance(content, str):
        return []

    domains: list[str] = []
    seen: set[str] = set()

    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines and comments (#, !, ;)
        if not line or line.startswith(("#", "!", ";")):
            continue

        # Strip trailing comments
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if not line:
            continue

        candidate: str | None = None

        # 1. Hosts format: "0.0.0.0 example.com"
        hosts_match = HOSTS_LINE_REGEX.match(line)
        if hosts_match:
            candidate = hosts_match.group(1)
        # 2. Adblock format: "||example.com^"
        elif line.startswith("||"):
            adblock_match = ADBLOCK_REGEX.match(line)
            if adblock_match:
                candidate = adblock_match.group(1)
        # 3. Plain domain line or space-separated line
        else:
            # If line has multiple whitespace-separated tokens, take the first non-IP token
            tokens = line.split()
            candidate = tokens[0] if tokens else None

        if not candidate:
            continue

        candidate_lower = candidate.strip().lower()
        if candidate_lower in IGNORED_HOSTNAMES:
            continue

        try:
            normalized = normalize_domain(candidate)
            if normalized in seen or normalized in IGNORED_HOSTNAMES:
                continue
            validate_domain(normalized)
            seen.add(normalized)
            domains.append(normalized)
        except InvalidDomainError:
            # Skip invalid domain lines gracefully during bulk feed parsing
            continue

    return domains
