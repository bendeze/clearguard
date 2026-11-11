package com.clearguard.app.data.repository

import com.clearguard.app.data.local.dao.BlocklistDao
import com.clearguard.app.data.local.entity.BlocklistEntity
import com.clearguard.app.data.remote.ClearGuardApi
import com.clearguard.app.data.remote.model.AuthTokenResponse
import com.clearguard.app.data.remote.model.BlocklistResponse
import com.clearguard.app.data.remote.model.DeactivationInitiateRequest
import com.clearguard.app.data.remote.model.DeactivationStatusResponse
import com.clearguard.app.data.remote.model.DeviceRegisterRequest
import com.clearguard.app.data.remote.model.DeviceRegisterResponse
import com.clearguard.app.data.remote.model.EncryptedVaultDto
import com.clearguard.app.data.remote.model.HealthResponse
import com.clearguard.app.data.remote.model.LoginRequest
import com.clearguard.app.data.remote.model.ReadinessResponse
import com.clearguard.app.data.remote.model.RefreshTokenRequest
import com.clearguard.app.data.remote.model.RegisterRequest
import com.clearguard.app.data.remote.model.SyncBatchCheckRequest
import com.clearguard.app.data.remote.model.SyncBatchCheckResponse
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import okhttp3.ResponseBody.Companion.toResponseBody
import retrofit2.Response
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

    override suspend fun getHealth(): HealthResponse {
        return HealthResponse(status = "ok", version = "0.6.0")
    }

    override suspend fun getLiveness(): Response<Unit> {
        return Response.success(Unit)
    }

    override suspend fun getReadiness(): ReadinessResponse {
        return ReadinessResponse(status = "ok", database = "connected")
    }

    override suspend fun register(request: RegisterRequest): AuthTokenResponse {
        return AuthTokenResponse("access-123", "refresh-123", "bearer", 3600)
    }

    override suspend fun login(request: LoginRequest): AuthTokenResponse {
        return AuthTokenResponse("access-123", "refresh-123", "bearer", 3600)
    }

    override suspend fun refreshToken(request: RefreshTokenRequest): AuthTokenResponse {
        return AuthTokenResponse("access-456", "refresh-456", "bearer", 3600)
    }

    override suspend fun registerDevice(request: DeviceRegisterRequest): Response<DeviceRegisterResponse> {
        return Response.success(DeviceRegisterResponse("registered", request.deviceIdentifier))
    }

    override suspend fun checkBatchSync(request: SyncBatchCheckRequest): SyncBatchCheckResponse {
        return SyncBatchCheckResponse(results = emptyList())
    }

    override suspend fun downloadBlocklistRaw(
        blocklistId: String,
        format: String,
        etag: String?,
        accept: String
    ): Response<okhttp3.ResponseBody> {
        return Response.error(404, "".toResponseBody(null))
    }

    override suspend fun getEncryptedVault(bearerToken: String): EncryptedVaultDto {
        return EncryptedVaultDto("", "", "", "", 100000)
    }

    override suspend fun syncEncryptedVault(
        bearerToken: String,
        vault: EncryptedVaultDto
    ): Response<Unit> {
        return Response.success(Unit)
    }

    override suspend fun requestDeactivation(
        bearerToken: String,
        request: DeactivationInitiateRequest
    ): DeactivationStatusResponse {
        return DeactivationStatusResponse("req-123", "user-1", "pending_partner_approval", "2026-11-09T18:00:00Z", 60)
    }

    override suspend fun getDeactivationStatus(bearerToken: String): DeactivationStatusResponse {
        return DeactivationStatusResponse("req-123", "user-1", "pending_partner_approval", "2026-11-09T18:00:00Z", 60)
    }

    override suspend fun cancelDeactivation(bearerToken: String): Response<Unit> {
        return Response.success(Unit)
    }
}
