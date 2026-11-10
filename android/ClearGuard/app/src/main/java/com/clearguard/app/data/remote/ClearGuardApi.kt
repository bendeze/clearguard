package com.clearguard.app.data.remote

import com.clearguard.app.data.remote.model.BlocklistResponse
import com.clearguard.app.data.remote.model.DeactivationInitiateRequest
import com.clearguard.app.data.remote.model.DeactivationStatusResponse
import com.clearguard.app.data.remote.model.EncryptedVaultDto
import com.clearguard.app.data.remote.model.HealthResponse
import com.clearguard.app.data.remote.model.ReadinessResponse
import com.clearguard.app.data.remote.model.SyncBatchCheckRequest
import com.clearguard.app.data.remote.model.SyncBatchCheckResponse
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming

interface ClearGuardApi {

    // Legacy Fallback Endpoint
    @GET("api/v1/blocklist")
    suspend fun getBlocklist(): BlocklistResponse

    // =========================================================================
    // 1. HEALTH & SYSTEM PROBES
    // =========================================================================
    @GET("api/v1/health")
    suspend fun getHealth(): HealthResponse

    @GET("api/v1/health/live")
    suspend fun getLiveness(): Response<Unit>

    @GET("api/v1/health/ready")
    suspend fun getReadiness(): ReadinessResponse

    // =========================================================================
    // 2. BLOCKLIST SYNCHRONIZATION (B3-B5)
    // =========================================================================
    @POST("api/v1/sync/batch")
    suspend fun checkBatchSync(
        @Body request: SyncBatchCheckRequest
    ): SyncBatchCheckResponse

    @Streaming
    @GET("api/v1/sync/blocklists/{id}/download")
    suspend fun downloadBlocklistRaw(
        @Path("id") blocklistId: String,
        @Query("format") format: String = "raw",
        @Header("If-None-Match") etag: String?,
        @Header("Accept") accept: String = "text/plain"
    ): Response<ResponseBody>

    // =========================================================================
    // 3. END-TO-END ENCRYPTED (E2EE) VAULT (Milestone B6)
    // =========================================================================
    @GET("api/v1/vault")
    suspend fun getEncryptedVault(
        @Header("Authorization") bearerToken: String
    ): EncryptedVaultDto

    @PUT("api/v1/vault")
    suspend fun syncEncryptedVault(
        @Header("Authorization") bearerToken: String,
        @Body vault: EncryptedVaultDto
    ): Response<Unit>

    // =========================================================================
    // 4. ACCOUNTABILITY & DEACTIVATION SYNCHRONIZATION (Milestone B6)
    // =========================================================================
    @POST("api/v1/accountability/request-deactivation")
    suspend fun requestDeactivation(
        @Header("Authorization") bearerToken: String,
        @Body request: DeactivationInitiateRequest
    ): DeactivationStatusResponse

    @GET("api/v1/accountability/status")
    suspend fun getDeactivationStatus(
        @Header("Authorization") bearerToken: String
    ): DeactivationStatusResponse

    @POST("api/v1/accountability/cancel-deactivation")
    suspend fun cancelDeactivation(
        @Header("Authorization") bearerToken: String
    ): Response<Unit>
}
