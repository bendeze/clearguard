package com.clearguard.app.domain.security

import android.content.Context
import android.content.Intent
import com.clearguard.app.domain.pledge.PledgeVerificationEngine
import com.clearguard.app.service.receiver.ClearGuardDeviceAdmin
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.mockito.Mockito.mock
import java.util.concurrent.TimeUnit

class MilestoneA6ValidationTest {

    @Test
    fun milestoneA6_completeCoSigningAnd60DayDelayWorkflow_validatesSuccessfully() {
        val pledgeText = "I am committed to living a clean, porn-free life."
        val userInputPledge = "  $pledgeText  "
        val isPledgeValid = PledgeVerificationEngine.verifyPledgeMatch(userInputPledge, pledgeText)
        assertTrue(isPledgeValid)

        val partnerPin = "9876"
        val pinHash = BiometricAuthManager.hashPin(partnerPin)
        val testInputHash = BiometricAuthManager.hashPin("9876")
        assertEquals(pinHash, testInputHash)

        val requestTime = System.currentTimeMillis()
        val remainingDaysAtStart = DeactivationDelayEngine.getDaysRemaining(requestTime, requestTime)
        assertEquals(60, remainingDaysAtStart)

        val thirtyDaysLater = requestTime + TimeUnit.DAYS.toMillis(30)
        val remainingDaysAt30 = DeactivationDelayEngine.getDaysRemaining(requestTime, thirtyDaysLater)
        assertEquals(30, remainingDaysAt30)
        assertFalse(DeactivationDelayEngine.isDeactivationAllowed(requestTime, thirtyDaysLater))

        val sixtyOneDaysLater = requestTime + TimeUnit.DAYS.toMillis(61)
        assertTrue(DeactivationDelayEngine.isDeactivationAllowed(requestTime, sixtyOneDaysLater))

        val adminReceiver = ClearGuardDeviceAdmin()
        val mockContext = mock(Context::class.java)
        val mockIntent = mock(Intent::class.java)
        val warningMessage = adminReceiver.onDisableRequested(mockContext, mockIntent)

        assertNotNull(warningMessage)
        assertTrue(warningMessage.toString().contains("60-day"))
    }
}
