"""REST API endpoints for blocklist synchronization, update checking, and rule distribution."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Path, Query, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.database import DbSession
from app.schemas.sync import (
    BlocklistDownloadResponse,
    SyncBatchCheckRequest,
    SyncBatchCheckResponse,
    SyncCheckItem,
    SyncCheckResponse,
)
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["Synchronization"])


@router.post(
    "/check",
    summary="Check blocklist update status",
    description="Evaluate client's installed blocklist against latest release.",
)
async def check_sync_status(
    session: DbSession,
    item: SyncCheckItem,
) -> SyncCheckResponse:
    """Evaluate sync status for a single blocklist collection."""
    service = SyncService(session)
    return await service.check_single_blocklist(item)


@router.post(
    "/batch",
    summary="Batch check blocklist updates",
    description="Evaluate sync status for multiple blocklists in a single HTTP request.",
)
async def batch_check_sync_status(
    session: DbSession,
    request: SyncBatchCheckRequest,
) -> SyncBatchCheckResponse:
    """Evaluate sync status across multiple subscribed blocklists."""
    service = SyncService(session)
    return await service.check_batch_blocklists(request)


@router.get(
    "/blocklists/{blocklist_id}/latest",
    summary="Get latest blocklist release metadata",
    description="Inspect the latest published version metadata, domain count, and content hash.",
)
async def get_latest_blocklist_metadata(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Unique UUID of the blocklist collection")],
) -> SyncCheckResponse:
    """Retrieve metadata of the latest published release for a blocklist."""
    service = SyncService(session)
    return await service.get_latest_metadata(blocklist_id)


@router.get(
    "/blocklists/{blocklist_id}/download",
    summary="Download blocklist filtering rules",
    description="Download active filtering domains in JSON or raw plain text, with ETag caching.",
    responses={
        200: {
            "content": {
                "application/json": {"schema": BlocklistDownloadResponse.model_json_schema()},
                "text/plain": {
                    "schema": {"type": "string", "example": "example1.com\nexample2.com"}
                },
            },
            "description": "Blocklist domain rules and integrity headers.",
        },
        304: {
            "description": "Not Modified. Local client blocklist snapshot is already up to date.",
        },
    },
)
async def download_blocklist(
    session: DbSession,
    blocklist_id: Annotated[uuid.UUID, Path(description="Unique UUID of the blocklist collection")],
    version: Annotated[
        str | None,
        Query(
            max_length=50,
            description="Specific release version to download (defaults to latest published)",
        ),
    ] = None,
    format: Annotated[
        str | None,
        Query(
            description="Payload delivery format: 'json' or 'raw'. Defaults to 'json'.",
        ),
    ] = None,
    if_none_match: Annotated[
        str | None,
        Header(alias="If-None-Match", description="Client ETag cache validator"),
    ] = None,
    accept: Annotated[
        str | None,
        Header(alias="Accept", description="Content-Type negotiation header"),
    ] = None,
) -> Response:
    """Download blocklist domain rules in JSON or raw plain-text format with ETag caching."""
    service = SyncService(session)
    blocklist, target_version, domains = await service.get_blocklist_download(
        blocklist_id=blocklist_id, version=version
    )

    etag = f'"{target_version.content_hash}"'
    response_headers = {
        "ETag": etag,
        "X-Content-Hash": target_version.content_hash,
        "X-Blocklist-Version": target_version.version,
        "X-Domain-Count": str(len(domains)),
        "Cache-Control": "public, max-age=3600",
    }

    # Conditional HTTP caching check
    if if_none_match:
        client_tag = if_none_match.strip()
        if (
            client_tag == "*"
            or client_tag == etag
            or client_tag.strip('"') == target_version.content_hash
        ):
            return Response(
                status_code=status.HTTP_304_NOT_MODIFIED,
                headers=response_headers,
            )

    is_raw = (format and format.lower() == "raw") or (
        accept and "text/plain" in accept and (not format or format.lower() != "json")
    )

    if is_raw:
        return PlainTextResponse(
            content="\n".join(domains),
            media_type="text/plain",
            headers=response_headers,
        )

    download_payload = BlocklistDownloadResponse(
        blocklist_id=blocklist.id,
        name=blocklist.name,
        version=target_version.version,
        content_hash=target_version.content_hash,
        domain_count=len(domains),
        published_at=target_version.created_at,
        changelog=target_version.changelog,
        domains=domains,
    )

    return JSONResponse(
        content=download_payload.model_dump(mode="json"),
        headers=response_headers,
    )
