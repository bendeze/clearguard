package com.clearguard.app.domain.model

/**
 * Represents the current status of adult content filtering protection.
 */
enum class ProtectionStatus {
    ACTIVE,
    INACTIVE,
    CONNECTING;

    val isProtected: Boolean
        get() = this == ACTIVE
}
