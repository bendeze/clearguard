"""Common and reusable Pydantic schemas for pagination, metadata, and errors."""

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    model_config = ConfigDict(extra="forbid")

    offset: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip before selecting results.",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of records to return (1 to 1000).",
    )


class PaginatedResponse[T](BaseModel):
    """Generic envelope for paginated resource collections."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T] = Field(description="List of records in the current page.")
    total: int = Field(ge=0, description="Total number of records available.")
    offset: int = Field(ge=0, description="Offset index for this page.")
    limit: int = Field(ge=1, description="Limit applied to this page.")
    has_more: bool = Field(description="Whether more records exist beyond this page.")

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        offset: int,
        limit: int,
    ) -> "PaginatedResponse[T]":
        """Convenience factory to compute has_more and instantiate PaginatedResponse."""
        has_more = (offset + len(items)) < total
        return cls(
            items=list(items),
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more,
        )


class ErrorDetail(BaseModel):
    """Detailed error object within the standard error envelope."""

    model_config = ConfigDict(extra="allow")

    code: str = Field(description="Unique application machine-readable error code.")
    message: str = Field(description="Human-readable explanation of the error.")
    details: Any = Field(
        default=None,
        description="Optional granular error context, field issues, or debugging data.",
    )


class ErrorResponse(BaseModel):
    """Standardized top-level API error response envelope."""

    error: ErrorDetail = Field(description="Error payload.")
