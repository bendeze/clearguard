package com.clearguard.app.data.repository

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.clearguard.app.domain.repository.SecureStorageRepository
import com.clearguard.app.domain.security.BiometricAuthManager
import dagger.hilt.android.qualifiers.ApplicationContext
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SecureStorageRepositoryImpl @Inject constructor(
    @param:ApplicationContext private val context: Context
) : SecureStorageRepository {

    private val prefs: SharedPreferences by lazy {
        try {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()

            EncryptedSharedPreferences.create(
                context,
                "clearguard_secure_prefs",
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (_: Exception) {
            context.getSharedPreferences("clearguard_secure_prefs_fallback", Context.MODE_PRIVATE)
        }
    }

    override suspend fun saveCommitmentPledge(phrase: String) {
        prefs.edit().putString(KEY_COMMITMENT_PLEDGE, phrase).apply()
    }

    override suspend fun getCommitmentPledge(): String? {
        return prefs.getString(KEY_COMMITMENT_PLEDGE, null)
    }

    override suspend fun hasCommitmentPledge(): Boolean {
        return !prefs.getString(KEY_COMMITMENT_PLEDGE, null).isNullOrEmpty()
    }

    override suspend fun clearCommitmentPledge() {
        prefs.edit().remove(KEY_COMMITMENT_PLEDGE).apply()
    }

    override suspend fun savePartnerPin(pin: String) {
        val hashed = BiometricAuthManager.hashPin(pin)
        prefs.edit().putString(KEY_PARTNER_PIN_HASH, hashed).apply()
    }

    override suspend fun verifyPartnerPin(pin: String): Boolean {
        val storedHash = prefs.getString(KEY_PARTNER_PIN_HASH, null) ?: return false
        val inputHash = BiometricAuthManager.hashPin(pin)
        return storedHash == inputHash
    }

    override suspend fun hasPartnerPin(): Boolean {
        return !prefs.getString(KEY_PARTNER_PIN_HASH, null).isNullOrEmpty()
    }

    override suspend fun clearPartnerPin() {
        prefs.edit().remove(KEY_PARTNER_PIN_HASH).apply()
    }

    override suspend fun savePartnerEmail(email: String) {
        prefs.edit().putString(KEY_PARTNER_EMAIL, email.trim()).apply()
    }

    override suspend fun getPartnerEmail(): String? {
        return prefs.getString(KEY_PARTNER_EMAIL, null)
    }

    override suspend fun hasPartnerEmail(): Boolean {
        return !prefs.getString(KEY_PARTNER_EMAIL, null).isNullOrEmpty()
    }

    override suspend fun clearPartnerEmail() {
        prefs.edit().remove(KEY_PARTNER_EMAIL).apply()
    }

    override suspend fun requestDeactivation() {
        prefs.edit().putLong(KEY_DEACTIVATION_TIMESTAMP, System.currentTimeMillis()).apply()
    }

    override suspend fun getDeactivationRequestTimestamp(): Long? {
        val value = prefs.getLong(KEY_DEACTIVATION_TIMESTAMP, -1L)
        return if (value != -1L) value else null
    }

    override suspend fun cancelDeactivationRequest() {
        prefs.edit().remove(KEY_DEACTIVATION_TIMESTAMP).apply()
    }

    override suspend fun isDeactivationRequested(): Boolean {
        return prefs.getLong(KEY_DEACTIVATION_TIMESTAMP, -1L) != -1L
    }

    override suspend fun saveAuthTokens(accessToken: String, refreshToken: String) {
        prefs.edit()
            .putString(KEY_ACCESS_TOKEN, accessToken)
            .putString(KEY_REFRESH_TOKEN, refreshToken)
            .apply()
    }

    override suspend fun getAccessToken(): String? {
        return prefs.getString(KEY_ACCESS_TOKEN, null)
    }

    override suspend fun getRefreshToken(): String? {
        return prefs.getString(KEY_REFRESH_TOKEN, null)
    }

    override suspend fun clearAuthTokens() {
        prefs.edit()
            .remove(KEY_ACCESS_TOKEN)
            .remove(KEY_REFRESH_TOKEN)
            .apply()
    }

    override suspend fun isAuthenticated(): Boolean {
        return !prefs.getString(KEY_ACCESS_TOKEN, null).isNullOrEmpty()
    }

    override suspend fun getOrCreateDeviceIdentifier(): String {
        var deviceId = prefs.getString(KEY_DEVICE_IDENTIFIER, null)
        if (deviceId.isNullOrEmpty()) {
            deviceId = "android-" + UUID.randomUUID().toString()
            prefs.edit().putString(KEY_DEVICE_IDENTIFIER, deviceId).apply()
        }
        return deviceId
    }

    companion object {
        private const val KEY_COMMITMENT_PLEDGE = "key_commitment_pledge"
        private const val KEY_PARTNER_PIN_HASH = "key_partner_pin_hash"
        private const val KEY_PARTNER_EMAIL = "key_partner_email"
        private const val KEY_DEACTIVATION_TIMESTAMP = "key_deactivation_timestamp"
        private const val KEY_ACCESS_TOKEN = "key_access_token"
        private const val KEY_REFRESH_TOKEN = "key_refresh_token"
        private const val KEY_DEVICE_IDENTIFIER = "key_device_identifier"
    }
}
