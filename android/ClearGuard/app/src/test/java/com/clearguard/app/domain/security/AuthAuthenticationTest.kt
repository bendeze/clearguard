package com.clearguard.app.domain.security

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AuthAuthenticationTest {

    @Test
    fun registerValidation_validInput_returnsTrue() {
        val username = "john_doe"
        val password = "SecurePassword123!"

        val isValid = username.length >= 3 && password.length >= 8
        assertTrue(isValid)
    }

    @Test
    fun registerValidation_shortPassword_returnsFalse() {
        val username = "john_doe"
        val password = "123"

        val isValid = username.length >= 3 && password.length >= 8
        assertFalse(isValid)
    }
}
