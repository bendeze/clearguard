package com.clearguard.app.domain.security

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.TimeUnit

class DeactivationDelayEngineTest {

    private val now = System.currentTimeMillis()

    @Test
    fun getRemainingMillis_requestJustCreated_returns60DaysInMs() {
        val remaining = DeactivationDelayEngine.getRemainingMillis(now, now)
        assertEquals(DeactivationDelayEngine.SIXTY_DAYS_MS, remaining)
    }

    @Test
    fun getDaysRemaining_request30DaysOld_returns30Days() {
        val thirtyDaysMs = TimeUnit.DAYS.toMillis(30)
        val requestTime = now - thirtyDaysMs
        val days = DeactivationDelayEngine.getDaysRemaining(requestTime, now)
        assertEquals(30, days)
    }

    @Test
    fun isDeactivationAllowed_60DaysElapsed_returnsTrue() {
        val sixtyOneDaysMs = TimeUnit.DAYS.toMillis(61)
        val requestTime = now - sixtyOneDaysMs
        val allowed = DeactivationDelayEngine.isDeactivationAllowed(requestTime, now)
        assertTrue(allowed)
    }

    @Test
    fun isDeactivationAllowed_lessThan60DaysElapsed_returnsFalse() {
        val tenDaysMs = TimeUnit.DAYS.toMillis(10)
        val requestTime = now - tenDaysMs
        val allowed = DeactivationDelayEngine.isDeactivationAllowed(requestTime, now)
        assertFalse(allowed)
    }
}
