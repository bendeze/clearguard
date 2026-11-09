package com.clearguard.app.service.work

import android.content.Context
import androidx.work.ListenableWorker.Result
import androidx.work.WorkerParameters
import com.clearguard.app.domain.repository.BlocklistRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test
import org.mockito.Mockito.mock

class BlocklistSyncWorkerTest {

    private lateinit var mockContext: Context
    private lateinit var mockWorkerParams: WorkerParameters
    private lateinit var fakeRepository: FakeSyncBlocklistRepository

    @Before
    fun setUp() {
        mockContext = mock(Context::class.java)
        mockWorkerParams = mock(WorkerParameters::class.java)
        fakeRepository = FakeSyncBlocklistRepository()
    }

    @Test
    fun doWork_syncSuccessful_returnsSuccess() = runTest {
        fakeRepository.shouldSucceed = true
        val worker = BlocklistSyncWorker(mockContext, mockWorkerParams, fakeRepository)

        val result = worker.doWork()

        assertEquals(Result.success(), result)
    }

    @Test
    fun doWork_syncFails_returnsRetry() = runTest {
        fakeRepository.shouldSucceed = false
        val worker = BlocklistSyncWorker(mockContext, mockWorkerParams, fakeRepository)

        val result = worker.doWork()

        assertEquals(Result.retry(), result)
    }
}

class FakeSyncBlocklistRepository : BlocklistRepository {
    var shouldSucceed: Boolean = true

    override fun getBlockedDomains(): Flow<List<String>> = flowOf(emptyList())

    override fun getBlockedCount(): Flow<Int> = flowOf(0)

    override suspend fun isDomainBlocked(domain: String): Boolean = false

    override suspend fun addDomain(domain: String) {}

    override suspend fun addDomains(domains: List<String>) {}

    override suspend fun removeDomain(domain: String) {}

    override suspend fun seedDefaultBlocklist() {}

    override suspend fun syncBlocklistFromBackend(): kotlin.Result<Int> {
        return if (shouldSucceed) {
            kotlin.Result.success(10)
        } else {
            kotlin.Result.failure(RuntimeException("Network error"))
        }
    }
}
