package com.clearguard.app.domain.pledge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PledgeVerificationEngineTest {

    private val pledge = "I am committed to living a clean, porn-free life."

    @Test
    fun verifyPledgeMatch_exactMatch_returnsTrue() {
        assertTrue(PledgeVerificationEngine.verifyPledgeMatch(pledge, pledge))
    }

    @Test
    fun verifyPledgeMatch_matchWithOuterWhitespace_returnsTrue() {
        assertTrue(PledgeVerificationEngine.verifyPledgeMatch("  $pledge  ", pledge))
    }

    @Test
    fun verifyPledgeMatch_caseMismatch_returnsFalse() {
        assertFalse(PledgeVerificationEngine.verifyPledgeMatch(pledge.lowercase(), pledge))
    }

    @Test
    fun verifyPledgeMatch_partialMatch_returnsFalse() {
        assertFalse(PledgeVerificationEngine.verifyPledgeMatch("I am committed to living clean.", pledge))
    }

    @Test
    fun verifyPledgeMatch_emptyInput_returnsFalse() {
        assertFalse(PledgeVerificationEngine.verifyPledgeMatch("", pledge))
    }

    @Test
    fun normalizePledgePhrase_trimsLeadingAndTrailingSpaces() {
        assertEquals("Hello World", PledgeVerificationEngine.normalizePledgePhrase("  Hello World  "))
    }
}
