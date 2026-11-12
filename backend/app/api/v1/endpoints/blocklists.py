"""REST API endpoints for blocklists, versioning, feed ingestion, and domain associations."""

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Query, UploadFile, status

from app.core.database import DbSession
from app.core.exceptions import ValidationError
from app.models.enums import DomainCategory
from app.schemas.blocklist import (
    BlocklistAssociateDomainsRequest,
    BlocklistCreate,
    BlocklistDomainsResponse,
    BlocklistListResponse,
    BlocklistPublishRequest,
    BlocklistRemoveDomainsRequest,
    BlocklistResponse,
    BlocklistRollbackRequest,
    BlocklistUpdate,
    BlocklistVersionListResponse,
    BlocklistVersionResponse,
    FeedIngestJobResponse,
    FeedIngestRequest,
    FeedIngestResponse,
    FeedIngestUrlRequest,
)
from app.schemas.domain import DomainResponse
from app.services.blocklist_service import BlocklistService
from app.services.feed_ingest_worker import MAX_FEED_BYTES, decode_feed_bytes

router = APIRouter(prefix="/blocklists", tags=["Blocklists"])


# ==============================================================================
# Blocklist CRUD Endpoints
# ==============================================================================


@router.get(
    "",
    summary="List Blocklists",
    description="Retrieve a paginated collection of registered blocklists.",
)
async def list_blocklists(
    session: DbSession,
    offset: Annotated[int, Query(ge=0, description="Offset index")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Page size limit")] = 50,
) -> BlocklistListResponse:
    """List blocklists with pagination."""
    service = BlocklistService(session)
    items = await service.list_blocklists(offset=offset, limit=limit)
    total = await service.count_blocklists()
    return BlocklistListResponse.create(
        items=[BlocklistResponse.model_validate(b) for b in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create Blocklist",
    description="Register a new filtering blocklist collection.",
)
async def create_blocklist(
    session: DbSession,
    data: BlocklistCreate,
) -> BlocklistResponse:
    """Create a new blocklist."""
    service = BlocklistService(session)
    blocklist = await service.create_blocklist(data)
    return BlocklistResponse.model_validate(blocklist)


@router.get(
    "/{blocklist_id}",
    summary="Get Blocklist",
    description="Retrieve detailed metadata for a specific blocklist by ID.",
)
async def get_blocklist(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
) -> BlocklistResponse:
    """Get blocklist by UUID."""
    service = BlocklistService(session)
    blocklist = await service.get_by_id(blocklist_id)
    return BlocklistResponse.model_validate(blocklist)


@router.put(
    "/{blocklist_id}",
    summary="Update Blocklist",
    description="Update metadata or active flags for a specific blocklist.",
)
async def update_blocklist(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    data: BlocklistUpdate,
) -> BlocklistResponse:
    """Update blocklist properties."""
    service = BlocklistService(session)
    blocklist = await service.update_blocklist(blocklist_id, data)
    return BlocklistResponse.model_validate(blocklist)


@router.delete(
    "/{blocklist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Blocklist",
    description="Delete a blocklist collection and all associated versions.",
)
async def delete_blocklist(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
) -> None:
    """Delete blocklist by UUID."""
    service = BlocklistService(session)
    await service.delete_blocklist(blocklist_id)


# ==============================================================================
# Blocklist Versioning Endpoints
# ==============================================================================


@router.get(
    "/{blocklist_id}/versions",
    summary="List Blocklist Versions",
    description="Retrieve paginated historical version releases for a blocklist.",
)
async def list_blocklist_versions(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    offset: Annotated[int, Query(ge=0, description="Offset index")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Page size limit")] = 50,
) -> BlocklistVersionListResponse:
    """List version snapshots for a blocklist."""
    service = BlocklistService(session)
    versions = await service.list_versions(blocklist_id, offset=offset, limit=limit)
    total = await service.count_versions(blocklist_id)
    return BlocklistVersionListResponse.create(
        items=[BlocklistVersionResponse.model_validate(v) for v in versions],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{blocklist_id}/versions/latest",
    summary="Get Latest Version",
    description="Retrieve the latest published version and SHA-256 integrity hash for client sync.",
)
async def get_latest_version(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
) -> BlocklistVersionResponse:
    """Get the latest release version snapshot for a blocklist."""
    service = BlocklistService(session)
    version = await service.get_latest_version(blocklist_id)
    return BlocklistVersionResponse.model_validate(version)


@router.post(
    "/{blocklist_id}/publish",
    status_code=status.HTTP_201_CREATED,
    summary="Publish Version",
    description="Compile active domains, compute SHA-256 hash, and release a new version snapshot.",
)
async def publish_version(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    request: BlocklistPublishRequest | None = None,
) -> BlocklistVersionResponse:
    """Release a new version snapshot."""
    service = BlocklistService(session)
    version_arg = request.version if request else None
    changelog_arg = request.changelog if request else None
    force_arg = request.force if request else False
    version = await service.publish_version(
        blocklist_id,
        version=version_arg,
        changelog=changelog_arg,
        force=force_arg,
    )
    return BlocklistVersionResponse.model_validate(version)


@router.post(
    "/{blocklist_id}/rollback",
    summary="Rollback Blocklist Version",
    description="Revert a blocklist's active pointer to a previously published snapshot version.",
)
async def rollback_version(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    request: BlocklistRollbackRequest,
) -> BlocklistVersionResponse:
    """Roll back blocklist active version pointer to a historical snapshot."""
    service = BlocklistService(session)
    version = await service.rollback_version(
        blocklist_id=blocklist_id,
        target_version_str=request.target_version,
        reason=request.reason,
    )
    return BlocklistVersionResponse.model_validate(version)


# ==============================================================================
# Domain Association & Ingestion Endpoints
# ==============================================================================


@router.get(
    "/{blocklist_id}/domains",
    summary="List Blocklist Domains",
    description="Retrieve a paginated collection of domains associated with a blocklist.",
)
async def get_blocklist_domains(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    offset: Annotated[int, Query(ge=0, description="Offset index")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Page size limit")] = 50,
) -> BlocklistDomainsResponse:
    """List domains associated with a blocklist."""
    service = BlocklistService(session)
    domains = await service.get_blocklist_domains(blocklist_id, offset=offset, limit=limit)
    total = await service.count_blocklist_domains(blocklist_id)
    return BlocklistDomainsResponse.create(
        items=[DomainResponse.model_validate(d) for d in domains],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/{blocklist_id}/domains",
    summary="Associate Domains",
    description="Associate existing domains with a blocklist.",
)
async def associate_domains(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    request: BlocklistAssociateDomainsRequest,
) -> dict[str, int]:
    """Associate domain IDs with a blocklist."""
    service = BlocklistService(session)
    count = await service.associate_domains(blocklist_id, request.domain_ids)
    return {"associated": count}


@router.delete(
    "/{blocklist_id}/domains",
    summary="Remove Associated Domains",
    description="Remove domain associations from a blocklist.",
)
async def remove_domains(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    request: BlocklistRemoveDomainsRequest,
) -> dict[str, int]:
    """Remove domain associations from a blocklist."""
    service = BlocklistService(session)
    count = await service.remove_domains(blocklist_id, request.domain_ids)
    return {"removed": count}


@router.post(
    "/{blocklist_id}/ingest",
    summary="Ingest Blocklist Feed",
    description="Parse raw feed content in Hosts, Adblock, or plain syntax and register domains.",
)
async def ingest_feed(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    request: FeedIngestRequest,
) -> FeedIngestResponse:
    """Ingest a raw blocklist feed and associate parsed domains."""
    service = BlocklistService(session)
    return await service.ingest_feed(blocklist_id, request)


@router.post(
    "/{blocklist_id}/ingest/file",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest Blocklist File (Background)",
    description="Upload a Hosts, Adblock, or plain domain list file for background ingestion.",
)
async def ingest_feed_file(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    file: Annotated[UploadFile, File(description="Text blocklist file (.txt, .hosts, .list)")],
    source: Annotated[str, Form(min_length=1, max_length=100)] = "file_upload",
    category: Annotated[DomainCategory, Form()] = DomainCategory.PORNOGRAPHY,
) -> FeedIngestJobResponse:
    """Upload a blocklist file and enqueue chunked background ingestion."""
    raw_bytes = await file.read(MAX_FEED_BYTES + 1)
    if len(raw_bytes) > MAX_FEED_BYTES:
        max_mb = MAX_FEED_BYTES // (1024 * 1024)
        raise ValidationError(
            message=f"Uploaded file exceeds maximum allowed size of {max_mb} MB.",
            details={"filename": file.filename},
        )

    content = decode_feed_bytes(raw_bytes)
    service = BlocklistService(session)
    job = await service.start_file_ingest_job(
        blocklist_id,
        content=content,
        filename=file.filename,
        source=source,
        category=category,
    )
    return FeedIngestJobResponse.model_validate(job)


@router.post(
    "/{blocklist_id}/ingest/url",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest Blocklist URL (Background)",
    description="Fetch a remote blocklist feed URL and ingest domains in background chunks.",
)
async def ingest_feed_url(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    request: FeedIngestUrlRequest,
) -> FeedIngestJobResponse:
    """Schedule background download and chunked ingestion from a remote feed URL."""
    service = BlocklistService(session)
    job = await service.start_url_ingest_job(blocklist_id, request)
    return FeedIngestJobResponse.model_validate(job)


@router.get(
    "/{blocklist_id}/ingest/jobs",
    summary="List Blocklist Ingestion Jobs",
    description="List recent background feed ingestion jobs for a blocklist.",
)
async def list_ingest_jobs(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[FeedIngestJobResponse]:
    """List recent background feed ingestion jobs."""
    service = BlocklistService(session)
    jobs = await service.list_ingest_jobs(blocklist_id, limit=limit)
    return [FeedIngestJobResponse.model_validate(j) for j in jobs]


@router.get(
    "/{blocklist_id}/ingest/jobs/{job_id}",
    summary="Get Blocklist Ingestion Job",
    description="Retrieve live progress and status for a specific background ingestion job.",
)
async def get_ingest_job(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Blocklist unique UUID")],
    job_id: Annotated[uuid.UUID, Path(description="Ingestion job unique UUID")],
) -> FeedIngestJobResponse:
    """Get a single background feed ingestion job."""
    service = BlocklistService(session)
    job = await service.get_ingest_job(blocklist_id, job_id)
    return FeedIngestJobResponse.model_validate(job)
