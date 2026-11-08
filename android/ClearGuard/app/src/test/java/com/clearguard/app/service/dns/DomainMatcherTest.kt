package com.clearguard.app.service.dns

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DomainMatcherTest {

    private val blocklist = setOf(
        "adultsite.com",
        "badcontent.net",
        "explicit.org"
    )

    @Test
    fun normalizeDomain_removesWwwAndTrailingDots() {
        assertEquals("example.com", DomainMatcher.normalizeDomain("www.example.com."))
        assertEquals("example.com", DomainMatcher.normalizeDomain("EXAMPLE.COM"))
    }

    @Test
    fun isBlocked_exactMatch_returnsTrue() {
        assertTrue(DomainMatcher.isBlocked("adultsite.com", blocklist))
        assertTrue(DomainMatcher.isBlocked("www.adultsite.com", blocklist))
    }

    @Test
    fun isBlocked_subdomainMatch_returnsTrue() {
        assertTrue(DomainMatcher.isBlocked("v1.video.adultsite.com", blocklist))
        assertTrue(DomainMatcher.isBlocked("cdn.badcontent.net", blocklist))
    }

    @Test
    fun isBlocked_allowedDomain_returnsFalse() {
        assertFalse(DomainMatcher.isBlocked("google.com", blocklist))
        assertFalse(DomainMatcher.isBlocked("wikipedia.org", blocklist))
        assertFalse(DomainMatcher.isBlocked("notadultsite.com", blocklist))
    }
}
