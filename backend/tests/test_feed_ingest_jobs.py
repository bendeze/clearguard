"""Integration and unit tests for background blocklist feed ingestion (file & URL)."""

import asyncio
import uuid

import pytest
from httpx import AsyncClient

from app.core.database import async_session_factory, engine
from app.models.base import Base
from app.repositories.blocklist_repository import BlocklistRepository
from app.services import feed_ingest_worker


@pytest.fixture
async def setup_database():
    """Ensure clean database schema before and after each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Wait for any in-flight background tasks before dropping tables
    if feed_ingest_worker._active_tasks:
        await asyncio.gather(*list(feed_ingest_worker._active_tasks), return_exceptions=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _create_test_blocklist(async_client: AsyncClient, name: str = "NSFW Test List") -> str:
    res = await async_client.post(
        "/api/v1/blocklists",
        json={"name": name, "description": "Test list", "is_default": False},
    )
    assert res.status_code == 201
    return res.json()["id"]


async def _wait_for_active_jobs() -> None:
    if feed_ingest_worker._active_tasks:
        await asyncio.gather(*list(feed_ingest_worker._active_tasks), return_exceptions=True)


@pytest.mark.anyio
async def test_ingest_feed_file_background_job(async_client: AsyncClient, setup_database) -> None:
    """Uploading a blocklist file should enqueue a background job and ingest all domains."""
    blocklist_id = await _create_test_blocklist(async_client)
    file_content = (
        b"# Comment line\n"
        b"0.0.0.0 bad-site-1.com\n"
        b"||bad-site-2.org^\n"
        b"bad-site-3.net\n"
        b"0.0.0.0 localhost\n"
    )

    res = await async_client.post(
        f"/api/v1/blocklists/{blocklist_id}/ingest/file",
        files={"file": ("nsfw_sample.txt", file_content, "text/plain")},
        data={"source": "sample_file", "category": "pornography"},
    )
    assert res.status_code == 202
    job = res.json()
    assert job["source_type"] == "file"
    assert job["filename"] == "nsfw_sample.txt"
    assert job["source_label"] == "sample_file"
    assert job["status"] in {"queued", "processing", "completed"}

    await _wait_for_active_jobs()

    job_res = await async_client.get(f"/api/v1/blocklists/{blocklist_id}/ingest/jobs/{job['id']}")
    assert job_res.status_code == 200
    finished = job_res.json()
    assert finished["status"] == "completed"
    assert finished["parsed_count"] == 3
    assert finished["processed_count"] == 3
    assert finished["new_domains_created"] == 3
    assert finished["domains_associated"] == 3
    assert finished["completed_at"] is not None

    list_res = await async_client.get(f"/api/v1/blocklists/{blocklist_id}/ingest/jobs")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    bl_res = await async_client.get(f"/api/v1/blocklists/{blocklist_id}")
    assert bl_res.status_code == 200
    assert bl_res.json()["domain_count"] == 3


@pytest.mark.anyio
async def test_ingest_feed_file_empty_rejected(async_client: AsyncClient, setup_database) -> None:
    """Uploading an empty file should return 422 validation error."""
    blocklist_id = await _create_test_blocklist(async_client)
    res = await async_client.post(
        f"/api/v1/blocklists/{blocklist_id}/ingest/file",
        files={"file": ("empty.txt", b"   \n", "text/plain")},
        data={"source": "empty_test", "category": "pornography"},
    )
    assert res.status_code == 422


@pytest.mark.anyio
async def test_ingest_feed_url_background_job(
    async_client: AsyncClient, setup_database, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Importing from a valid public URL should fetch and ingest domains in background."""
    blocklist_id = await _create_test_blocklist(async_client, name="URL Test List")

    async def fake_fetch(url: str, *, max_bytes: int = 0) -> str:
        assert url == "https://example.com/nsfw.txt"
        return "0.0.0.0 remote-a.com\n0.0.0.0 remote-b.com\n"

    monkeypatch.setattr(feed_ingest_worker, "fetch_feed_content", fake_fetch)

    res = await async_client.post(
        f"/api/v1/blocklists/{blocklist_id}/ingest/url",
        json={
            "url": "https://example.com/nsfw.txt",
            "source": "hagezi_nsfw",
            "category": "pornography",
        },
    )
    assert res.status_code == 202
    job = res.json()
    assert job["source_type"] == "url"
    assert job["source_url"] == "https://example.com/nsfw.txt"

    await _wait_for_active_jobs()

    job_res = await async_client.get(f"/api/v1/blocklists/{blocklist_id}/ingest/jobs/{job['id']}")
    assert job_res.status_code == 200
    finished = job_res.json()
    assert finished["status"] == "completed"
    assert finished["parsed_count"] == 2
    assert finished["processed_count"] == 2
    assert finished["new_domains_created"] == 2
    assert finished["domains_associated"] == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    "bad_url",
    [
        "ftp://example.com/hosts.txt",
        "http://localhost/hosts.txt",
        "http://127.0.0.1/hosts.txt",
        "http://10.0.0.1/hosts.txt",
        "http://192.168.1.10/hosts.txt",
    ],
)
async def test_ingest_feed_url_rejects_unsafe_urls(
    async_client: AsyncClient, setup_database, bad_url: str
) -> None:
    """Private, loopback, and non-HTTP URLs must be rejected for SSRF protection."""
    blocklist_id = await _create_test_blocklist(async_client, name=f"SSRF {bad_url}")
    res = await async_client.post(
        f"/api/v1/blocklists/{blocklist_id}/ingest/url",
        json={"url": bad_url, "source": "unsafe", "category": "pornography"},
    )
    assert res.status_code == 422


@pytest.mark.anyio
async def test_process_feed_ingestion_job_multi_chunk(
    async_client: AsyncClient, setup_database
) -> None:
    """Chunked worker should process domains across multiple batches and update totals."""
    blocklist_id = uuid.UUID(await _create_test_blocklist(async_client, name="Chunked List"))

    async with async_session_factory() as session:
        repo = BlocklistRepository(session)
        job = await repo.create_ingestion_job(
            blocklist_id=blocklist_id,
            source_type="file",
            source_label="chunk_test",
            filename="big.txt",
            category="pornography",
            status="queued",
        )
        await session.commit()
        job_id = job.id

    content = "\n".join(f"chunk-domain-{i}.com" for i in range(5))
    await feed_ingest_worker.process_feed_ingestion_job(
        job_id,
        blocklist_id,
        content=content,
        source_label="chunk_test",
        category="pornography",
        session_factory=async_session_factory,
        chunk_size=2,
    )

    job_res = await async_client.get(f"/api/v1/blocklists/{blocklist_id}/ingest/jobs/{job_id}")
    assert job_res.status_code == 200
    finished = job_res.json()
    assert finished["status"] == "completed"
    assert finished["parsed_count"] == 5
    assert finished["processed_count"] == 5
    assert finished["new_domains_created"] == 5
    assert finished["domains_associated"] == 5


@pytest.mark.anyio
async def test_get_missing_ingest_job_returns_404(
    async_client: AsyncClient, setup_database
) -> None:
    """Requesting a nonexistent job ID should return 404."""
    blocklist_id = await _create_test_blocklist(async_client, name="Missing Job List")
    res = await async_client.get(f"/api/v1/blocklists/{blocklist_id}/ingest/jobs/{uuid.uuid4()}")
    assert res.status_code == 404
