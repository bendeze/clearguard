package com.clearguard.app.domain.pledge

object PledgeVerificationEngine {

    /**
     * Normalizes whitespace for pledge comparison by trimming leading and trailing whitespace.
     */
    fun normalizePledgePhrase(phrase: String): String {
        return phrase.trim()
    }

    /**
     * Enforces case-sensitive, exact character-for-character matching
     * between user input and the stored commitment pledge phrase.
     */
    fun verifyPledgeMatch(userInput: String, storedPledge: String): Boolean {
        val cleanInput = normalizePledgePhrase(userInput)
        val cleanStored = normalizePledgePhrase(storedPledge)
        return cleanInput.isNotEmpty() && cleanInput == cleanStored
    }
}
