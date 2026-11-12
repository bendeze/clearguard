package com.clearguard.app.domain.repository

interface SecureStorageRepository {
    suspend fun saveCommitmentPledge(phrase: String)
    suspend fun getCommitmentPledge(): String?
    suspend fun hasCommitmentPledge(): Boolean
    suspend fun clearCommitmentPledge()

    suspend fun savePartnerPin(pin: String)
    suspend fun verifyPartnerPin(pin: String): Boolean
    suspend fun hasPartnerPin(): Boolean
    suspend fun clearPartnerPin()

    suspend fun savePartnerEmail(email: String)
    suspend fun getPartnerEmail(): String?
    suspend fun hasPartnerEmail(): Boolean
    suspend fun clearPartnerEmail()

    suspend fun requestDeactivation()
    suspend fun getDeactivationRequestTimestamp(): Long?
    suspend fun cancelDeactivationRequest()
    suspend fun isDeactivationRequested(): Boolean

    suspend fun saveAuthTokens(accessToken: String, refreshToken: String)
    suspend fun getAccessToken(): String?
    suspend fun getRefreshToken(): String?
    suspend fun clearAuthTokens()
    suspend fun isAuthenticated(): Boolean
    suspend fun getOrCreateDeviceIdentifier(): String
}
