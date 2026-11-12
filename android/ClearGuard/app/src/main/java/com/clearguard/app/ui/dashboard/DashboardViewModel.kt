package com.clearguard.app.ui.dashboard

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.clearguard.app.data.remote.ClearGuardApi
import com.clearguard.app.data.remote.model.DeviceRegisterRequest
import com.clearguard.app.data.remote.model.LoginRequest
import com.clearguard.app.data.remote.model.RegisterRequest
import com.clearguard.app.domain.model.ProtectionStatus
import com.clearguard.app.domain.pledge.PledgeVerificationEngine
import com.clearguard.app.domain.repository.ProtectionRepository
import com.clearguard.app.domain.repository.SecureStorageRepository
import com.clearguard.app.domain.security.DeactivationDelayEngine
import com.clearguard.app.service.ClearGuardVpnService
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val protectionRepository: ProtectionRepository,
    private val secureStorageRepository: SecureStorageRepository,
    private val api: ClearGuardApi
) : ViewModel() {

    val uiState: StateFlow<ProtectionStatus> = protectionRepository
        .getProtectionStatus()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.Eagerly,
            initialValue = ProtectionStatus.INACTIVE
        )

    private val _deactivationDaysRemaining = MutableStateFlow<Int?>(null)
    val deactivationDaysRemaining: StateFlow<Int?> = _deactivationDaysRemaining.asStateFlow()

    init {
        checkDeactivationRequestStatus()
    }

    private fun checkDeactivationRequestStatus() {
        viewModelScope.launch {
            val timestamp = secureStorageRepository.getDeactivationRequestTimestamp()
            if (timestamp != null) {
                val days = DeactivationDelayEngine.getDaysRemaining(timestamp)
                _deactivationDaysRemaining.value = days
            } else {
                _deactivationDaysRemaining.value = null
            }
        }
    }

    suspend fun isAuthenticated(): Boolean {
        return secureStorageRepository.isAuthenticated()
    }

    suspend fun getDeviceUuid(): String {
        return secureStorageRepository.getOrCreateDeviceIdentifier()
    }

    suspend fun signOut() {
        secureStorageRepository.clearAuthTokens()
    }

    suspend fun isOnboardingCompleted(): Boolean {
        return secureStorageRepository.hasCommitmentPledge() &&
                secureStorageRepository.hasPartnerPin() &&
                secureStorageRepository.hasPartnerEmail()
    }

    suspend fun saveCommitmentPledge(phrase: String) {
        secureStorageRepository.saveCommitmentPledge(phrase)
    }

    suspend fun savePartnerPin(pin: String) {
        secureStorageRepository.savePartnerPin(pin)
    }

    suspend fun savePartnerEmail(email: String) {
        secureStorageRepository.savePartnerEmail(email)
    }

    suspend fun registerUser(username: String, email: String?, password: String): Result<Unit> {
        return try {
            val response = api.register(RegisterRequest(username = username, password = password, email = email))
            secureStorageRepository.saveAuthTokens(response.accessToken, response.refreshToken)

            val deviceId = secureStorageRepository.getOrCreateDeviceIdentifier()
            val deviceName = "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}"
            try {
                api.registerDevice(DeviceRegisterRequest(deviceIdentifier = deviceId, deviceName = deviceName, clientVersion = "0.7.0"))
            } catch (_: Exception) {}

            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun loginUser(username: String, password: String): Result<Unit> {
        return try {
            val deviceId = secureStorageRepository.getOrCreateDeviceIdentifier()
            val deviceName = "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}"
            val response = api.login(LoginRequest(username = username, password = password, deviceIdentifier = deviceId, deviceName = deviceName))
            secureStorageRepository.saveAuthTokens(response.accessToken, response.refreshToken)

            try {
                api.registerDevice(DeviceRegisterRequest(deviceIdentifier = deviceId, deviceName = deviceName, clientVersion = "0.7.0"))
            } catch (_: Exception) {}

            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun startVpnService(context: Context) {
        viewModelScope.launch {
            protectionRepository.setProtectionStatus(ProtectionStatus.ACTIVE)
            val intent = Intent(context, ClearGuardVpnService::class.java).apply {
                action = ClearGuardVpnService.ACTION_START
            }
            context.startService(intent)
        }
    }

    fun stopVpnService(context: Context) {
        viewModelScope.launch {
            protectionRepository.setProtectionStatus(ProtectionStatus.INACTIVE)
            val intent = Intent(context, ClearGuardVpnService::class.java).apply {
                action = ClearGuardVpnService.ACTION_STOP
            }
            context.startService(intent)
        }
    }

    suspend fun requestDeactivationWithCoSign(
        pledgeInput: String,
        partnerPinInput: String
    ): Result<Unit> {
        val storedPledge = secureStorageRepository.getCommitmentPledge() ?: ""
        val isPledgeMatch = PledgeVerificationEngine.verifyPledgeMatch(pledgeInput, storedPledge)
        val isPinMatch = secureStorageRepository.verifyPartnerPin(partnerPinInput)

        return if (isPledgeMatch && isPinMatch) {
            secureStorageRepository.requestDeactivation()
            checkDeactivationRequestStatus()
            Result.success(Unit)
        } else {
            Result.failure(IllegalArgumentException("Pledge phrase or Partner PIN is incorrect"))
        }
    }

    fun cancelDeactivationRequest() {
        viewModelScope.launch {
            secureStorageRepository.cancelDeactivationRequest()
            _deactivationDaysRemaining.value = null
        }
    }
}
