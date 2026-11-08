package com.clearguard.app.domain.model

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtectionStatusTest {

    @Test
    fun activeStatus_isProtectedReturnsTrue() {
        val status = ProtectionStatus.ACTIVE
        assertTrue(status.isProtected)
    }

    @Test
    fun inactiveStatus_isProtectedReturnsFalse() {
        val status = ProtectionStatus.INACTIVE
        assertFalse(status.isProtected)
    }

    @Test
    fun connectingStatus_isProtectedReturnsFalse() {
        val status = ProtectionStatus.CONNECTING
        assertFalse(status.isProtected)
    }
}
