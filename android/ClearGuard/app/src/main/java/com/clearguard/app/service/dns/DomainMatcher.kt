package com.clearguard.app.service.dns

object DomainMatcher {

    /**
     * Normalizes a domain name for consistent comparison.
     * Converts to lowercase, strips trailing dot, and removes leading 'www.' if present.
     */
    fun normalizeDomain(domain: String): String {
        var clean = domain.trim().lowercase()
        if (clean.endsWith(".")) {
            clean = clean.dropLast(1)
        }
        if (clean.startsWith("www.")) {
            clean = clean.drop(4)
        }
        return clean
    }

    /**
     * Checks if [domain] is blocked by the set of [blockedDomains].
     * Matches exact domains and subdomains (e.g., 'sub.adult.com' matches 'adult.com').
     */
    fun isBlocked(domain: String, blockedDomains: Set<String>): Boolean {
        val normalized = normalizeDomain(domain)
        if (normalized.isEmpty()) return false

        // Exact match check
        if (blockedDomains.contains(normalized)) return true

        // Parent domain / Subdomain check
        var current = normalized
        while (current.contains(".")) {
            current = current.substringAfter(".", "")
            if (current.isNotEmpty() && blockedDomains.contains(current)) {
                return true
            }
        }

        return false
    }
}
