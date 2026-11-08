package com.clearguard.app.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.clearguard.app.domain.model.ProtectionStatus
import com.clearguard.app.domain.repository.ProtectionRepository
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

    fun toggleProtection() {
        viewModelScope.launch {
            protectionRepository.toggleProtection()
        }
    }
}
