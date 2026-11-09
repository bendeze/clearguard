"""Enumerations for domain categorization and operational statuses."""

from enum import StrEnum


class DomainCategory(StrEnum):
    """Categorization for blocked domains."""

    PORNOGRAPHY = "pornography"
    EXPLICIT = "explicit"
    EROTICA = "erotica"
    MALWARE = "malware"
    UNSPECIFIED = "unspecified"


class DomainStatus(StrEnum):
    """Operational status of a domain in the filtering system."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_REVIEW = "pending_review"
    ALLOWLISTED = "allowlisted"
