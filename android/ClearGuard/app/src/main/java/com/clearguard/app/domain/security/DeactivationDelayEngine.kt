package com.clearguard.app.domain.security

import java.util.concurrent.TimeUnit

object DeactivationDelayEngine {

    const val SIXTY_DAYS_MS: Long = 60L * 24 * 60 * 60 * 1000

    /**
     * Calculates the remaining time in milliseconds before deactivation is allowed.
     */
    fun getRemainingMillis(requestTimestamp: Long, currentTimestamp: Long = System.currentTimeMillis()): Long {
        val elapsed = currentTimestamp - requestTimestamp
        val remaining = SIXTY_DAYS_MS - elapsed
        return if (remaining > 0) remaining else 0L
    }

    /**
     * Calculates the remaining number of full days before deactivation is allowed.
     */
    fun getDaysRemaining(requestTimestamp: Long, currentTimestamp: Long = System.currentTimeMillis()): Int {
        val remainingMs = getRemainingMillis(requestTimestamp, currentTimestamp)
        if (remainingMs <= 0) return 0
        return TimeUnit.MILLISECONDS.toDays(remainingMs).toInt()
    }

    /**
     * Returns true if the mandatory 60-day cool-off period has fully elapsed.
     */
    fun isDeactivationAllowed(requestTimestamp: Long, currentTimestamp: Long = System.currentTimeMillis()): Boolean {
        return getRemainingMillis(requestTimestamp, currentTimestamp) <= 0L
    }
}
