"""Application exceptions and global exception handlers."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ClearGuardException(Exception):
    """Base exception for all ClearGuard application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(ClearGuardException):
    """Exception raised when an entity or resource is not found."""

    def __init__(self, message: str = "Resource not found", details: Any = None) -> None:
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationError(ClearGuardException):
    """Exception raised for business validation failures."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details=details,
        )


class DatabaseError(ClearGuardException):
    """Exception raised for unexpected database operation errors."""

    def __init__(self, message: str = "A database error occurred", details: Any = None) -> None:
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class EntityNotFoundError(NotFoundError):
    """Exception raised when a specific database entity cannot be found."""

    def __init__(self, entity_name: str, identifier: Any = None) -> None:
        detail_msg = (
            f"{entity_name} with identifier '{identifier}' was not found"
            if identifier is not None
            else f"{entity_name} not found"
        )
        super().__init__(
            message=detail_msg,
            details={"entity": entity_name, "identifier": str(identifier) if identifier else None},
        )
        self.code = "ENTITY_NOT_FOUND"


class DuplicateEntityError(ClearGuardException):
    """Exception raised when a unique constraint is violated."""

    def __init__(self, message: str = "Entity already exists", details: Any = None) -> None:
        super().__init__(
            message=message,
            code="DUPLICATE_ENTITY",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class DatabaseConstraintError(ClearGuardException):
    """Exception raised when a check or foreign key constraint is violated."""

    def __init__(self, message: str = "Database constraint violation", details: Any = None) -> None:
        super().__init__(
            message=message,
            code="CONSTRAINT_VIOLATION",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


def _build_error_response(
    code: str, message: str, status_code: int, details: Any = None
) -> JSONResponse:
    """Format a consistent JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


async def clearguard_exception_handler(request: Request, exc: ClearGuardException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning(
        "ClearGuardException [%s]: %s (path=%s)",
        exc.code,
        exc.message,
        request.url.path,
    )
    return _build_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions consistently."""
    logger.warning(
        "HTTPException [%s]: %s (path=%s)",
        exc.status_code,
        exc.detail,
        request.url.path,
    )
    return _build_error_response(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic request validation exceptions."""
    logger.info("Validation error at %s: %s", request.url.path, exc.errors())
    return _build_error_response(
        code="REQUEST_VALIDATION_ERROR",
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught internal exceptions."""
    logger.exception("Unhandled server error at %s: %s", request.url.path, exc)
    return _build_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the application instance."""
    app.add_exception_handler(ClearGuardException, clearguard_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
