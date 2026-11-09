package com.clearguard.app.domain.repository

interface SecureStorageRepository {
    suspend fun saveCommitmentPledge(phrase: String)
    suspend fun getCommitmentPledge(): String?
    suspend fun hasCommitmentPledge(): Boolean
    suspend fun clearCommitmentPledge()
}
