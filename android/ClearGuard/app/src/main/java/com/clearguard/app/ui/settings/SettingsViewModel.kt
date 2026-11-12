package com.clearguard.app.ui.settings

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.clearguard.app.data.remote.ClearGuardApi
import com.clearguard.app.domain.repository.BlocklistRepository
import com.clearguard.app.domain.repository.SecureStorageRepository
import com.clearguard.app.service.work.BlocklistSyncWorker
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val blocklistRepository: BlocklistRepository,
    private val secureStorageRepository: SecureStorageRepository,
    private val api: ClearGuardApi,
    @param:ApplicationContext private val context: Context
) : ViewModel() {

    private val _isDarkTheme = MutableStateFlow(true)
    val isDarkTheme: StateFlow<Boolean> = _isDarkTheme.asStateFlow()

    private val _healthStatus = MutableStateFlow("Checking...")
    val healthStatus: StateFlow<String> = _healthStatus.asStateFlow()

    private val _isAuthenticated = MutableStateFlow(false)
    val isAuthenticated: StateFlow<Boolean> = _isAuthenticated.asStateFlow()

    private val _deviceUuid = MutableStateFlow("")
    val deviceUuid: StateFlow<String> = _deviceUuid.asStateFlow()

    private val _isSyncing = MutableStateFlow(false)
    val isSyncing: StateFlow<Boolean> = _isSyncing.asStateFlow()

    private val _syncResultMessage = MutableStateFlow<String?>(null)
    val syncResultMessage: StateFlow<String?> = _syncResultMessage.asStateFlow()

    init {
        viewModelScope.launch {
            blocklistRepository.seedDefaultBlocklist()
            checkAuthAndDeviceState()
            fetchBackendHealth()
        }
        schedulePeriodicSync()
    }

    private suspend fun checkAuthAndDeviceState() {
        _isAuthenticated.value = secureStorageRepository.isAuthenticated()
        _deviceUuid.value = secureStorageRepository.getOrCreateDeviceIdentifier()
    }

    private suspend fun fetchBackendHealth() {
        try {
            val response = api.getHealth()
            _healthStatus.value = "Online v${response.version}"
        } catch (_: Exception) {
            _healthStatus.value = "Offline / Local Only"
        }
    }

    val blocklistCount: StateFlow<Int> = blocklistRepository
        .getBlockedCount()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.Eagerly,
            initialValue = 0
        )

    fun toggleDarkTheme(enabled: Boolean) {
        _isDarkTheme.value = enabled
    }

    fun signOut() {
        viewModelScope.launch {
            secureStorageRepository.clearAuthTokens()
            _isAuthenticated.value = false
        }
    }

    fun triggerManualSync() {
        viewModelScope.launch {
            _isSyncing.value = true
            _syncResultMessage.value = null
            val result = blocklistRepository.syncBlocklistFromBackend()
            _isSyncing.value = false
            if (result.isSuccess) {
                val added = result.getOrNull() ?: 0
                _syncResultMessage.value = if (added > 0) {
                    "Blocklist updated: $added new rules added"
                } else {
                    "Blocklist is already up to date"
                }
            } else {
                _syncResultMessage.value = "Sync failed: ${result.exceptionOrNull()?.message ?: "Network error"}"
            }
        }
    }

    fun clearSyncResultMessage() {
        _syncResultMessage.value = null
    }

    fun schedulePeriodicSync() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val syncWorkRequest = PeriodicWorkRequestBuilder<BlocklistSyncWorker>(
            repeatInterval = 24,
            repeatIntervalTimeUnit = TimeUnit.HOURS
        )
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            BlocklistSyncWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            syncWorkRequest
        )
    }
}
