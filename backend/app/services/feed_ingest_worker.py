"""Background worker and helpers for chunked blocklist feed ingestion."""

import asyncio
import ipaddress
import logging
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import database
from app.core.exceptions import ValidationError
from app.models.blocklist import FeedIngestionJob
from app.repositories.blocklist_repository import BlocklistRepository
from app.repositories.domain_repository import DomainRepository
from app.services.feed_parser import parse_blocklist_feed

logger = logging.getLogger(__name__)

MAX_FEED_BYTES = 25 * 1024 * 1024  # 25 MB cap for uploaded or downloaded feeds
INGEST_CHUNK_SIZE = 1000

_active_tasks: set[asyncio.Task[None]] = set()


def validate_feed_url(raw_url: str) -> str:
    """Validate that a feed URL is public HTTP/HTTPS and not targeting local/private networks."""
    url = raw_url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError(
            message="Feed URL must be a valid http:// or https:// URL.",
            details={"url": url},
        )

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname or hostname in {"localhost", "localhost.localdomain"}:
        raise ValidationError(
            message="Localhost feed URLs are not permitted.",
            details={"url": url},
        )

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return url

    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        raise ValidationError(
            message="Private or reserved IP addresses are not permitted for feed URLs.",
            details={"url": url},
        )
    return url


def decode_feed_bytes(raw: bytes) -> str:
    """Decode feed bytes as UTF-8, falling back to Latin-1 if needed."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


async def fetch_feed_content(url: str, *, max_bytes: int = MAX_FEED_BYTES) -> str:
    """Download a remote blocklist feed with streaming size enforcement."""
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    headers = {"User-Agent": "ClearGuard-Ingest/1.0"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        async with client.stream("GET", url, headers=headers) as resp:
            resp.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                total += len(chunk)
                if total > max_bytes:
                    limit_mb = max_bytes // (1024 * 1024)
                    raise ValueError(f"Remote feed exceeds maximum allowed size of {limit_mb} MB.")
                chunks.append(chunk)
            return decode_feed_bytes(b"".join(chunks))


async def _update_job_fields(
    session_factory: async_sessionmaker[AsyncSession],
    job_id: uuid.UUID,
    **fields: object,
) -> None:
    """Persist status or counter updates for a FeedIngestionJob in its own transaction."""
    async with session_factory() as session:
        job = await session.get(FeedIngestionJob, job_id)
        if not job:
            return
        for key, value in fields.items():
            setattr(job, key, value)
        await session.commit()


async def _ingest_chunk(
    session_factory: async_sessionmaker[AsyncSession],
    blocklist_id: uuid.UUID,
    job_id: uuid.UUID,
    chunk: list[str],
    *,
    source_label: str,
    category: str,
) -> tuple[int, int]:
    """Insert new domains and associate one chunk with the blocklist, updating job progress."""
    async with session_factory() as session:
        domain_repo = DomainRepository(session)
        blocklist_repo = BlocklistRepository(session)

        existing_records = await domain_repo.get_by_domains(chunk)
        existing_map = {rec.domain: rec for rec in existing_records}

        new_names = [d for d in chunk if d not in existing_map]
        if new_names:
            domains_to_create = [
                {
                    "domain": d,
                    "category": category,
                    "status": "active",
                    "source": source_label,
                    "confidence_score": 1.0,
                }
                for d in new_names
            ]
            new_records = await domain_repo.bulk_create(domains_to_create)
            for rec in new_records:
                existing_map[rec.domain] = rec

        all_domain_ids = [existing_map[d].id for d in chunk if d in existing_map]
        associated_count = await blocklist_repo.add_domains(blocklist_id, all_domain_ids)

        job = await session.get(FeedIngestionJob, job_id)
        if job:
            job.processed_count += len(chunk)
            job.new_domains_created += len(new_names)
            job.domains_associated += associated_count

        await session.commit()
        return len(new_names), associated_count


async def process_feed_ingestion_job(
    job_id: uuid.UUID,
    blocklist_id: uuid.UUID,
    *,
    content: str | None = None,
    url: str | None = None,
    source_label: str,
    category: str,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    chunk_size: int = INGEST_CHUNK_SIZE,
) -> None:
    """Execute a background feed ingestion job in bounded database chunks."""
    factory = session_factory or database.async_session_factory
    try:
        raw_content = content
        if url is not None:
            await _update_job_fields(factory, job_id, status="downloading")
            raw_content = await fetch_feed_content(url)

        parsed_domains = parse_blocklist_feed(raw_content or "")
        await _update_job_fields(
            factory,
            job_id,
            status="processing",
            parsed_count=len(parsed_domains),
        )

        for idx in range(0, len(parsed_domains), chunk_size):
            chunk = parsed_domains[idx : idx + chunk_size]
            await _ingest_chunk(
                factory,
                blocklist_id,
                job_id,
                chunk,
                source_label=source_label,
                category=category,
            )

        await _update_job_fields(
            factory,
            job_id,
            status="completed",
            completed_at=datetime.now(UTC),
        )
    except Exception as exc:
        logger.exception("Background feed ingestion job %s failed", job_id)
        await _update_job_fields(
            factory,
            job_id,
            status="failed",
            error_message=str(exc)[:1000],
            completed_at=datetime.now(UTC),
        )


def schedule_feed_ingestion_job(
    job_id: uuid.UUID,
    blocklist_id: uuid.UUID,
    *,
    content: str | None = None,
    url: str | None = None,
    source_label: str,
    category: str,
) -> asyncio.Task[None]:
    """Schedule a background asyncio task and retain a strong reference until completion."""
    task = asyncio.create_task(
        process_feed_ingestion_job(
            job_id,
            blocklist_id,
            content=content,
            url=url,
            source_label=source_label,
            category=category,
        )
    )
    _active_tasks.add(task)
    task.add_done_callback(_active_tasks.discard)
    return task
