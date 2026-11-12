package com.clearguard.app.data.repository

import com.clearguard.app.data.local.dao.BlocklistDao
import com.clearguard.app.data.local.entity.BlocklistEntity
import com.clearguard.app.data.remote.ClearGuardApi
import com.clearguard.app.data.remote.model.SyncBatchCheckRequest
import com.clearguard.app.data.remote.model.SyncItemDto
import com.clearguard.app.domain.repository.BlocklistRepository
import com.clearguard.app.service.dns.DomainMatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.InputStreamReader
import java.security.MessageDigest
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BlocklistRepositoryImpl @Inject constructor(
    private val blocklistDao: BlocklistDao,
    private val api: ClearGuardApi
) : BlocklistRepository {

    private val defaultSeedDomains = listOf(
        "pornhub.com",
        "xvideos.com",
        "xnxx.com",
        "xhamster.com",
        "redtube.com",
        "youporn.com",
        "tube8.com",
        "spankbang.com",
        "brazzers.com",
        "chaturbate.com"
    )

    private var cachedEtag: String? = null

    override fun getBlockedDomains(): Flow<List<String>> {
        return blocklistDao.getAllBlockedDomains().map { entities ->
            entities.map { it.domain }
        }
    }

    override fun getBlockedCount(): Flow<Int> {
        return blocklistDao.getAllBlockedDomains().map { entities ->
            entities.size
        }
    }

    override suspend fun isDomainBlocked(domain: String): Boolean {
        val normalized = DomainMatcher.normalizeDomain(domain)
        return blocklistDao.isDomainBlocked(normalized)
    }

    override suspend fun addDomain(domain: String) {
        val normalized = DomainMatcher.normalizeDomain(domain)
        if (normalized.isNotEmpty()) {
            blocklistDao.insertDomains(listOf(BlocklistEntity(domain = normalized)))
        }
    }

    override suspend fun addDomains(domains: List<String>) {
        val entities = domains
            .map { DomainMatcher.normalizeDomain(it) }
            .filter { it.isNotEmpty() }
            .map { BlocklistEntity(domain = it) }
        if (entities.isNotEmpty()) {
            blocklistDao.insertDomains(entities)
        }
    }

    override suspend fun removeDomain(domain: String) {
        val normalized = DomainMatcher.normalizeDomain(domain)
        blocklistDao.deleteDomain(normalized)
    }

    override suspend fun seedDefaultBlocklist() {
        addDomains(defaultSeedDomains)
    }

    override suspend fun syncBlocklistFromBackend(): Result<Int> = withContext(Dispatchers.IO) {
        try {
            // Step 1: Issue Batch Sync Check Handshake
            val syncRequest = SyncBatchCheckRequest(
                items = listOf(
                    SyncItemDto(
                        blocklistId = DEFAULT_BLOCKLIST_ID,
                        clientVersion = "1.0.0",
                        currentHash = ""
                    )
                )
            )

            val batchResponse = try {
                api.checkBatchSync(syncRequest)
            } catch (_: Exception) {
                null
            }

            val targetItem = batchResponse?.results?.firstOrNull()

            // If backend reports up to date, skip download
            if (targetItem != null && targetItem.status == "up_to_date") {
                return@withContext Result.success(0)
            }

            // Step 2: Stream Download Raw Text Domain Payload
            val downloadResponse = api.downloadBlocklistRaw(
                blocklistId = DEFAULT_BLOCKLIST_ID,
                format = "raw",
                etag = cachedEtag
            )

            if (downloadResponse.code() == 304) { // HTTP 304 Not Modified
                return@withContext Result.success(0)
            }

            val body = downloadResponse.body()
            if (downloadResponse.isSuccessful && body != null) {
                val newEtag = downloadResponse.headers()["ETag"]
                if (!newEtag.isNullOrEmpty()) {
                    cachedEtag = newEtag
                }

                val expectedHash = downloadResponse.headers()["X-Content-Hash"]
                val digest = MessageDigest.getInstance("SHA-256")

                val newDomains = mutableListOf<String>()
                val reader = BufferedReader(InputStreamReader(body.byteStream()))

                reader.forEachLine { line ->
                    val domain = line.trim()
                    if (domain.isNotEmpty() && !domain.startsWith("#")) {
                        digest.update(domain.toByteArray())
                        newDomains.add(domain)
                    }
                }

                val computedHash = digest.digest().joinToString("") { "%02x".format(it) }
                val isHashValid = expectedHash.isNullOrEmpty() || expectedHash == computedHash

                if (isHashValid && newDomains.isNotEmpty()) {
                    addDomains(newDomains)
                    return@withContext Result.success(newDomains.size)
                }
            }

            // Step 3: Fallback to Legacy Endpoint if Stream Sync returns empty
            val fallbackResponse = api.getBlocklist()
            if (fallbackResponse.domains.isNotEmpty()) {
                addDomains(fallbackResponse.domains)
                Result.success(fallbackResponse.domains.size)
            } else {
                Result.failure(IllegalStateException("Empty blocklist received from backend"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    companion object {
        private const val DEFAULT_BLOCKLIST_ID = "00000000-0000-0000-0000-000000000001"
    }
}
