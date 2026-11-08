package com.clearguard.app.data.repository

import com.clearguard.app.domain.model.ProtectionStatus
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class ProtectionRepositoryTest {

    private lateinit var repository: ProtectionRepositoryImpl

    @Before
    fun setUp() {
        repository = ProtectionRepositoryImpl()
    }

    @Test
    fun initialStatus_isInactive() = runTest {
        val status = repository.getProtectionStatus().first()
        assertEquals(ProtectionStatus.INACTIVE, status)
    }

    @Test
    fun toggleProtection_changesInactiveToActive() = runTest {
        repository.toggleProtection()
        val status = repository.getProtectionStatus().first()
        assertEquals(ProtectionStatus.ACTIVE, status)
    }

    @Test
    fun toggleProtection_changesActiveToInactive() = runTest {
        repository.setProtectionStatus(ProtectionStatus.ACTIVE)
        repository.toggleProtection()
        val status = repository.getProtectionStatus().first()
        assertEquals(ProtectionStatus.INACTIVE, status)
    }
}
