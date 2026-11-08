package com.clearguard.app.data.repository

import com.clearguard.app.domain.model.ProtectionStatus
import com.clearguard.app.domain.repository.ProtectionRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ProtectionRepositoryImpl @Inject constructor() : ProtectionRepository {
    private val _protectionStatus = MutableStateFlow(ProtectionStatus.INACTIVE)

    override fun getProtectionStatus(): Flow<ProtectionStatus> = _protectionStatus.asStateFlow()

    override suspend fun toggleProtection() {
        val current = _protectionStatus.value
        _protectionStatus.value = if (current == ProtectionStatus.ACTIVE) {
            ProtectionStatus.INACTIVE
        } else {
            ProtectionStatus.ACTIVE
        }
    }

    override suspend fun setProtectionStatus(status: ProtectionStatus) {
        _protectionStatus.value = status
    }
}
