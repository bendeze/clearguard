package com.clearguard.app.data.repository

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.clearguard.app.domain.repository.SecureStorageRepository
import dagger.hilt.android.qualifiers.ApplicationContext
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

    companion object {
        private const val KEY_COMMITMENT_PLEDGE = "key_commitment_pledge"
    }
}
