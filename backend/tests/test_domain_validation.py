"""Tests for domain normalization and RFC 1035/1123 validation engine."""

import pytest

from app.core.exceptions import InvalidDomainError
from app.services.domain_validator import (
    normalize_and_validate_domain,
    normalize_domain,
    validate_domain,
)

# --- Normalization Tests ---


def test_normalize_strips_schemes() -> None:
    """Verify standard URL schemes are stripped."""
    assert normalize_domain("http://example.com") == "example.com"
    assert normalize_domain("https://example.com") == "example.com"
    assert normalize_domain("ftp://example.com") == "example.com"
    assert normalize_domain("H2://EXAMPLE.COM") == "example.com"


def test_normalize_strips_ports_and_paths() -> None:
    """Verify ports, paths, queries, and fragments are stripped."""
    assert normalize_domain("example.com:8080") == "example.com"
    assert normalize_domain("http://example.com:443/login?redirect=true#section") == "example.com"
    assert normalize_domain("sub.example.com/path/to/resource") == "sub.example.com"


def test_normalize_www_prefix() -> None:
    """Verify www. prefix is removed while preserving non-www subdomains."""
    assert normalize_domain("www.example.com") == "example.com"
    assert normalize_domain("WWW.PORN-SITE.XXX") == "porn-site.xxx"
    assert normalize_domain("media.example.com") == "media.example.com"
    assert normalize_domain("www.sub.example.com") == "sub.example.com"


def test_normalize_whitespace_and_dots() -> None:
    """Verify surrounding whitespace and dots are trimmed."""
    assert normalize_domain("   .example.com.   ") == "example.com"
    assert normalize_domain("\n\texample.org.\r\n") == "example.org"


def test_normalize_punycode_idn() -> None:
    """Verify internationalized domain names are encoded to Punycode ASCII."""
    assert normalize_domain("müller.com") == "xn--mller-kva.com"
    assert normalize_domain("https://BÜCHER.DE") == "xn--bcher-kva.de"


def test_normalize_empty_input_raises_invalid_domain() -> None:
    """Verify empty or non-string inputs raise InvalidDomainError."""
    with pytest.raises(InvalidDomainError, match="non-empty string"):
        normalize_domain("")

    with pytest.raises(InvalidDomainError, match="non-empty string"):
        normalize_domain("   ")

    with pytest.raises(InvalidDomainError, match="Domain is empty"):
        normalize_domain("http://")


# --- RFC Validation Tests ---


def test_validate_valid_domains() -> None:
    """Verify valid multi-label domains pass validation."""
    valid_domains = [
        "example.com",
        "porn-site.xxx",
        "sub.domain.co.uk",
        "xn--mller-kva.com",
        "a-b-c.adult.org",
        "123-site.com",
        "streaming.video.porn",
    ]
    for domain in valid_domains:
        validate_domain(domain)


def test_validate_rejects_ip_addresses() -> None:
    """Verify IPv4 and IPv6 addresses are rejected as domain names."""
    with pytest.raises(InvalidDomainError, match="IP addresses are not permitted"):
        validate_domain("192.168.1.1")

    with pytest.raises(InvalidDomainError, match="IP addresses are not permitted"):
        validate_domain("127.0.0.1")

    with pytest.raises(InvalidDomainError, match="IP addresses are not permitted"):
        validate_domain("::1")


def test_validate_rejects_single_label() -> None:
    """Verify single-label hostnames without TLD are rejected."""
    with pytest.raises(InvalidDomainError, match="at least a domain name and a top-level domain"):
        validate_domain("localhost")

    with pytest.raises(InvalidDomainError, match="at least a domain name and a top-level domain"):
        validate_domain("adultsite")


def test_validate_rejects_numeric_tld() -> None:
    """Verify all-numeric TLDs are rejected according to RFC 1123."""
    with pytest.raises(InvalidDomainError, match="TLD.*cannot be numeric"):
        validate_domain("example.123")


def test_validate_rejects_consecutive_dots() -> None:
    """Verify empty labels created by consecutive dots are rejected."""
    with pytest.raises(InvalidDomainError, match="consecutive dots"):
        validate_domain("example..com")


def test_validate_rejects_invalid_characters_and_hyphens() -> None:
    """Verify labels with invalid symbols or misplaced hyphens are rejected."""
    invalid_cases = [
        "-example.com",
        "example-.com",
        "exam_ple.com",
        "exam ple.com",
        "example.c",  # TLD < 2 chars
    ]
    for case in invalid_cases:
        with pytest.raises(InvalidDomainError):
            validate_domain(case)


def test_validate_rejects_oversized_labels_and_domains() -> None:
    """Verify RFC length limits are enforced (63 chars per label, 253 overall)."""
    oversized_label = "a" * 64 + ".com"
    with pytest.raises(InvalidDomainError, match="exceeds maximum length of 63 characters"):
        validate_domain(oversized_label)

    oversized_domain = ("a" * 60 + ".") * 4 + "com"  # 248 chars (ok)
    validate_domain(oversized_domain)

    extreme_domain = ("a" * 60 + ".") * 5 + "com"  # > 253 chars
    with pytest.raises(InvalidDomainError, match="exceeds maximum length of 253 characters"):
        validate_domain(extreme_domain)


def test_normalize_and_validate_pipeline() -> None:
    """Verify end-to-end normalization and validation."""
    result = normalize_and_validate_domain("  HTTPS://WWW.Adult-Portal.XXX:443/home  ")
    assert result == "adult-portal.xxx"
