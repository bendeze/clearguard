package com.clearguard.app.domain.security

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class BiometricAuthManagerTest {

    @Test
    fun hashPin_samePin_returnsSameHash() {
        val hash1 = BiometricAuthManager.hashPin("1234")
        val hash2 = BiometricAuthManager.hashPin("1234")
        assertEquals(hash1, hash2)
    }

    @Test
    fun hashPin_differentPins_returnDifferentHashes() {
        val hash1 = BiometricAuthManager.hashPin("1234")
        val hash2 = BiometricAuthManager.hashPin("5678")
        assertNotEquals(hash1, hash2)
    }

    @Test
    fun hashPin_returns64CharHexHash() {
        val hash = BiometricAuthManager.hashPin("1234")
        assertEquals(64, hash.length)
    }
}
