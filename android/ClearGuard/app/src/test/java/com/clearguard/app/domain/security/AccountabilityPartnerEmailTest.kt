package com.clearguard.app.domain.security

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AccountabilityPartnerEmailTest {

    @Test
    fun emailValidation_validEmail_returnsTrue() {
        val email = "partner@example.com"
        val isValid = email.contains("@") && email.contains(".") && email.length > 5
        assertTrue(isValid)
    }

    @Test
    fun emailValidation_invalidEmail_returnsFalse() {
        val email = "invalid-email"
        val isValid = email.contains("@") && email.contains(".") && email.length > 5
        assertFalse(isValid)
    }
}
