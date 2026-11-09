"""Database error translation utilities for SQLAlchemy exceptions."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.exc import DBAPIError, IntegrityError, NoResultFound, SQLAlchemyError

from app.core.exceptions import (
    ClearGuardException,
    DatabaseConstraintError,
    DatabaseError,
    DuplicateEntityError,
    EntityNotFoundError,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def translate_database_errors(
    entity_name: str = "Entity",
) -> AsyncGenerator[None, None]:
    """Context manager translating low-level SQLAlchemy errors to application domain exceptions."""
    try:
        yield
    except ClearGuardException:
        # Re-raise already converted domain exceptions
        raise
    except IntegrityError as exc:
        orig_msg = str(exc.orig).lower() if exc.orig else str(exc).lower()
        logger.warning("Database integrity error on [%s]: %s", entity_name, orig_msg)
        if "unique" in orig_msg or "duplicate" in orig_msg:
            raise DuplicateEntityError(
                message=f"{entity_name} already exists or violates a uniqueness constraint.",
                details={"error": orig_msg},
            ) from exc
        raise DatabaseConstraintError(
            message=f"Database constraint violation on {entity_name}.",
            details={"error": orig_msg},
        ) from exc
    except NoResultFound as exc:
        logger.info("No database result found for [%s]", entity_name)
        raise EntityNotFoundError(entity_name=entity_name) from exc
    except (DBAPIError, SQLAlchemyError) as exc:
        logger.exception("Underlying database operation failed for [%s]: %s", entity_name, exc)
        raise DatabaseError(
            message=f"A database error occurred while processing {entity_name}.",
            details={"error": str(exc)},
        ) from exc
