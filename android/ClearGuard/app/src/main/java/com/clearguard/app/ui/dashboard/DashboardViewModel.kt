package com.clearguard.app.ui.dashboard

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.clearguard.app.domain.model.ProtectionStatus
import com.clearguard.app.domain.repository.ProtectionRepository
import com.clearguard.app.service.ClearGuardVpnService
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val protectionRepository: ProtectionRepository
) : ViewModel() {

    val uiState: StateFlow<ProtectionStatus> = protectionRepository
        .getProtectionStatus()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.Eagerly,
            initialValue = ProtectionStatus.INACTIVE
        )

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
}
