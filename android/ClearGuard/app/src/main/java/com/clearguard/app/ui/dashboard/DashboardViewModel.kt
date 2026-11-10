package com.clearguard.app.ui.dashboard

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
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
    private val secureStorageRepository: SecureStorageRepository
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
