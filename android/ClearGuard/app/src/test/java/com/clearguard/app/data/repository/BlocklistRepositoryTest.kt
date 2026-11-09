package com.clearguard.app.data.repository

import com.clearguard.app.data.local.dao.BlocklistDao
import com.clearguard.app.data.local.entity.BlocklistEntity
import com.clearguard.app.data.remote.ClearGuardApi
import com.clearguard.app.data.remote.model.BlocklistResponse
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class BlocklistRepositoryTest {

    private lateinit var fakeDao: FakeBlocklistDao
    private lateinit var fakeApi: FakeClearGuardApi
    private lateinit var repository: BlocklistRepositoryImpl

    @Before
    fun setUp() {
        fakeDao = FakeBlocklistDao()
        fakeApi = FakeClearGuardApi()
        repository = BlocklistRepositoryImpl(fakeDao, fakeApi)
    }

    @Test
    fun seedDefaultBlocklist_insertsDefaultDomains() = runTest {
        repository.seedDefaultBlocklist()
        val count = repository.getBlockedCount().first()
        assertTrue(count > 0)
    }

    @Test
    fun addDomain_normalizesAndInsertsDomain() = runTest {
        repository.addDomain("www.badsite.com.")
        val isBlocked = repository.isDomainBlocked("badsite.com")
        assertTrue(isBlocked)
    }

    @Test
    fun removeDomain_deletesDomain() = runTest {
        repository.addDomain("badsite.com")
        repository.removeDomain("badsite.com")
        val isBlocked = repository.isDomainBlocked("badsite.com")
        assertFalse(isBlocked)
    }

    @Test
    fun syncBlocklistFromBackend_fetchesAndInsertsRemoteDomains() = runTest {
        fakeApi.remoteDomains = listOf("remote-adult-1.com", "remote-adult-2.com")
        val result = repository.syncBlocklistFromBackend()

        assertTrue(result.isSuccess)
        assertEquals(2, result.getOrNull())
        assertTrue(repository.isDomainBlocked("remote-adult-1.com"))
    }
}

class FakeBlocklistDao : BlocklistDao {
    private val domains = MutableStateFlow<List<BlocklistEntity>>(emptyList())

    override fun getAllBlockedDomains(): Flow<List<BlocklistEntity>> = domains

    override suspend fun isDomainBlocked(domain: String): Boolean {
        return domains.value.any { it.domain == domain }
    }

    override suspend fun insertDomains(domains: List<BlocklistEntity>) {
        val current = this.domains.value.toMutableList()
        domains.forEach { newEntity ->
            if (current.none { it.domain == newEntity.domain }) {
                current.add(newEntity)
            }
        }
        this.domains.value = current
    }

    override suspend fun deleteDomain(domain: String) {
        val current = this.domains.value.toMutableList()
        current.removeAll { it.domain == domain }
        this.domains.value = current
    }

    override suspend fun clearAll() {
        this.domains.value = emptyList()
    }
}

class FakeClearGuardApi : ClearGuardApi {
    var remoteDomains: List<String> = emptyList()

    override suspend fun getBlocklist(): BlocklistResponse {
        return BlocklistResponse(
            version = "1.0",
            domains = remoteDomains,
            totalCount = remoteDomains.size
        )
    }
}
