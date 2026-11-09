package com.clearguard.app.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.clearguard.app.domain.repository.BlocklistRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val blocklistRepository: BlocklistRepository
) : ViewModel() {

    init {
        viewModelScope.launch {
            blocklistRepository.seedDefaultBlocklist()
        }
    }

    val blocklistCount: StateFlow<Int> = blocklistRepository
        .getBlockedCount()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.Eagerly,
            initialValue = 0
        )
}
