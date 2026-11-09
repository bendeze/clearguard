"""Domain normalization and RFC 1035/1123 validation engine."""

import ipaddress
import re

import idna

from app.core.exceptions import InvalidDomainError

# Regex for matching individual RFC-compliant domain labels
LABEL_REGEX = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


def normalize_domain(raw_domain: str) -> str:
    """Normalize a raw domain or URL string into a canonical lowercase domain.

    Rules applied:
    - Strips whitespace.
    - Strips URL protocol schemes (http://, https://, etc.).
    - Strips URL paths, query parameters, and fragments.
    - Strips port numbers (:80, :443, :8080).
    - Converts to lowercase.
    - Strips leading 'www.' if present and not the entire domain.
    - Encodes Internationalized Domain Names (IDN) to Punycode ASCII.
    - Strips leading and trailing dots.
    """
    if not raw_domain or not isinstance(raw_domain, str) or not raw_domain.strip():
        raise InvalidDomainError(str(raw_domain), "Domain input must be a non-empty string.")

    cleaned = raw_domain.strip().lower()

    # Remove protocol prefix (e.g. http://, https://, h2://, ftp://)
    cleaned = re.sub(r"^[a-z][a-z0-9+.-]*://", "", cleaned)

    # Remove userinfo (e.g. user:pass@)
    if "@" in cleaned:
        cleaned = cleaned.split("@", 1)[-1]

    # Remove path, query string, and fragment
    for delimiter in ("/", "?", "#"):
        if delimiter in cleaned:
            cleaned = cleaned.split(delimiter, 1)[0]

    # Remove port number (e.g., :8080)
    if ":" in cleaned:
        cleaned = cleaned.split(":", 1)[0]

    # Strip leading and trailing dots
    cleaned = cleaned.strip(".")

    # Strip leading www. if followed by at least two parts (e.g. www.example.com -> example.com)
    if cleaned.startswith("www.") and len(cleaned) > 4 and "." in cleaned[4:]:
        cleaned = cleaned[4:]

    if not cleaned:
        raise InvalidDomainError(raw_domain, "Domain is empty after normalization.")

    # Convert IDN / Unicode domains to Punycode ASCII
    try:
        cleaned = idna.encode(cleaned, uts46=True).decode("ascii")
    except (idna.IDNAError, UnicodeError) as exc:
        raise InvalidDomainError(
            raw_domain, f"Invalid internationalized domain name: {exc}"
        ) from exc

    return cleaned


def validate_domain(domain: str) -> None:
    """Validate that a normalized domain adheres to RFC 1035 / RFC 1123 standards.

    Validation rules:
    - Rejects raw IP addresses (IPv4 and IPv6).
    - Length must be between 1 and 253 characters.
    - Must consist of at least two labels (domain name and TLD).
    - Each label must be 1 to 63 characters long.
    - Labels must contain only alphanumeric characters and internal hyphens.
    - TLD must not be all-numeric and must have at least 2 characters.
    """
    if not domain or not isinstance(domain, str):
        raise InvalidDomainError(str(domain), "Domain cannot be empty.")

    # 1. Reject IP addresses (ClearGuard filters by domain, not IP)
    try:
        ipaddress.ip_address(domain)
        raise InvalidDomainError(domain, "IP addresses are not permitted as domain names.")
    except ValueError:
        pass

    # 2. Total domain length check (RFC 1035: maximum 253 characters)
    if len(domain) > 253:
        raise InvalidDomainError(domain, "Domain exceeds maximum length of 253 characters.")

    # 3. Label inspection
    labels = domain.split(".")
    if len(labels) < 2:
        raise InvalidDomainError(
            domain,
            "Domain must contain at least a domain name and a top-level domain "
            "(e.g., 'example.com').",
        )

    tld = labels[-1]
    # TLD cannot be all-numeric (RFC 1123)
    if tld.isdigit():
        raise InvalidDomainError(domain, "Top-level domain (TLD) cannot be numeric.")

    if len(tld) < 2:
        raise InvalidDomainError(
            domain, "Top-level domain (TLD) must be at least 2 characters long."
        )

    for label in labels:
        if not label:
            raise InvalidDomainError(domain, "Domain contains empty label (consecutive dots).")
        if len(label) > 63:
            raise InvalidDomainError(
                domain, f"Label '{label}' exceeds maximum length of 63 characters."
            )
        if not LABEL_REGEX.match(label):
            raise InvalidDomainError(
                domain,
                f"Label '{label}' contains invalid characters or leading/trailing hyphens.",
            )


def normalize_and_validate_domain(raw_domain: str) -> str:
    """Normalize raw domain input and validate standard RFC structure."""
    normalized = normalize_domain(raw_domain)
    validate_domain(normalized)
    return normalized
