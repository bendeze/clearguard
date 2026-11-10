package com.clearguard.app.data.remote.model

import com.google.gson.annotations.SerializedName

data class BlocklistResponse(
    @SerializedName("version") val version: String,
    @SerializedName("domains") val domains: List<String>,
    @SerializedName("total_count") val totalCount: Int
)

data class HealthResponse(
    @SerializedName("status") val status: String,
    @SerializedName("version") val version: String
)

data class ReadinessResponse(
    @SerializedName("status") val status: String,
    @SerializedName("database") val database: String
)

data class SyncItemDto(
    @SerializedName("blocklist_id") val blocklistId: String,
    @SerializedName("client_version") val clientVersion: String,
    @SerializedName("current_hash") val currentHash: String
)

data class SyncBatchCheckRequest(
    @SerializedName("items") val items: List<SyncItemDto>
)

data class SyncBatchItemResult(
    @SerializedName("blocklist_id") val blocklistId: String,
    @SerializedName("status") val status: String,
    @SerializedName("latest_version") val latestVersion: String?,
    @SerializedName("latest_hash") val latestHash: String?,
    @SerializedName("download_url") val downloadUrl: String?
)

data class SyncBatchCheckResponse(
    @SerializedName("results") val results: List<SyncBatchItemResult>
)

data class EncryptedVaultDto(
    @SerializedName("ciphertext") val ciphertext: String,
    @SerializedName("iv") val iv: String,
    @SerializedName("tag") val tag: String,
    @SerializedName("salt") val salt: String,
    @SerializedName("kdf_iterations") val kdfIterations: Int
)

data class DeactivationInitiateRequest(
    @SerializedName("partner_email") val partnerEmail: String
)

data class DeactivationStatusResponse(
    @SerializedName("request_id") val requestId: String,
    @SerializedName("started_at") val startedAt: Long,
    @SerializedName("cooloff_days") val cooloffDays: Int,
    @SerializedName("partner_status") val partnerStatus: String
)
