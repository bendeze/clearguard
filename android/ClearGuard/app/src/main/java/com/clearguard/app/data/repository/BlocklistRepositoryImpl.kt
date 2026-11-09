package com.clearguard.app.data.repository

import com.clearguard.app.data.local.dao.BlocklistDao
import com.clearguard.app.data.local.entity.BlocklistEntity
import com.clearguard.app.domain.repository.BlocklistRepository
import com.clearguard.app.service.dns.DomainMatcher
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BlocklistRepositoryImpl @Inject constructor(
    private val blocklistDao: BlocklistDao
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
}
