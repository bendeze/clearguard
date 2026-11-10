"""Blocklist synchronization service managing update evaluations, batch sync, and rule delivery."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.models.blocklist import Blocklist, BlocklistVersion
from app.repositories.blocklist_repository import BlocklistRepository
from app.schemas.sync import (
    SyncBatchCheckRequest,
    SyncBatchCheckResponse,
    SyncCheckItem,
    SyncCheckResponse,
)
from app.services.version_comparator import determine_sync_status

logger = logging.getLogger(__name__)


class SyncService:
    """Service handling synchronization handshake protocol and distribution."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = BlocklistRepository(session)

    async def check_single_blocklist(self, item: SyncCheckItem) -> SyncCheckResponse:
        """Evaluate synchronization status for a single blocklist collection."""
        await self.repository.get_by_id_or_raise(item.blocklist_id)

        latest = await self.repository.get_latest_version(item.blocklist_id)
        if latest is None:
            raise EntityNotFoundError("BlocklistVersion", item.blocklist_id)

        status, update_required = determine_sync_status(
            client_version=item.client_version,
            client_hash=item.client_content_hash,
            latest_version=latest.version,
            latest_hash=latest.content_hash,
        )

        return SyncCheckResponse(
            blocklist_id=item.blocklist_id,
            status=status,
            update_required=update_required,
            latest_version=latest.version,
            latest_content_hash=latest.content_hash,
            domain_count=latest.domain_count,
            changelog=latest.changelog,
            download_url=f"/api/v1/sync/blocklists/{item.blocklist_id}/download",
        )

    async def check_batch_blocklists(
        self, request: SyncBatchCheckRequest
    ) -> SyncBatchCheckResponse:
        """Evaluate synchronization status for multiple blocklists in a single request."""
        results: list[SyncCheckResponse] = []
        for item in request.items:
            evaluation = await self.check_single_blocklist(item)
            results.append(evaluation)

        return SyncBatchCheckResponse(items=results)

    async def get_latest_metadata(self, blocklist_id: uuid.UUID) -> SyncCheckResponse:
        """Retrieve latest release metadata and status evaluation for a blocklist."""
        check_item = SyncCheckItem(
            blocklist_id=blocklist_id,
            client_version=None,
            client_content_hash=None,
        )
        return await self.check_single_blocklist(check_item)

    async def get_blocklist_download(
        self, blocklist_id: uuid.UUID, version: str | None = None
    ) -> tuple[Blocklist, BlocklistVersion, list[str]]:
        """Retrieve blocklist entity, target release version, and sorted active domains."""
        blocklist = await self.repository.get_by_id_or_raise(blocklist_id)

        if version:
            target_version = await self.repository.get_version(blocklist_id, version)
            if target_version is None:
                raise EntityNotFoundError("BlocklistVersion", f"{blocklist_id}/{version}")
        else:
            target_version = await self.repository.get_latest_version(blocklist_id)
            if target_version is None:
                raise EntityNotFoundError("BlocklistVersion", blocklist_id)

        domains = await self.repository.get_domain_names(blocklist_id)
        return blocklist, target_version, domains

