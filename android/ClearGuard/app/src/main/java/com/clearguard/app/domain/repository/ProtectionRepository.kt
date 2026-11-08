package com.clearguard.app.domain.repository

import com.clearguard.app.domain.model.ProtectionStatus
import kotlinx.coroutines.flow.Flow

interface ProtectionRepository {
    fun getProtectionStatus(): Flow<ProtectionStatus>
    suspend fun toggleProtection()
    suspend fun setProtectionStatus(status: ProtectionStatus)
}
