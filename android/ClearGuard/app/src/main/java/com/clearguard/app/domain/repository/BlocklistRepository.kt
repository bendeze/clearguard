package com.clearguard.app.domain.repository

import kotlinx.coroutines.flow.Flow

interface BlocklistRepository {
    fun getBlockedDomains(): Flow<List<String>>
    fun getBlockedCount(): Flow<Int>
    suspend fun isDomainBlocked(domain: String): Boolean
    suspend fun addDomain(domain: String)
    suspend fun addDomains(domains: List<String>)
    suspend fun removeDomain(domain: String)
    suspend fun seedDefaultBlocklist()
    suspend fun syncBlocklistFromBackend(): Result<Int>
}
