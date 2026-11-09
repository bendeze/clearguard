package com.clearguard.app.service.receiver

import android.content.Context
import android.content.Intent
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.mockito.Mockito.mock

class ClearGuardDeviceAdminTest {

    private lateinit var adminReceiver: ClearGuardDeviceAdmin
    private lateinit var mockContext: Context

    @Before
    fun setUp() {
        adminReceiver = ClearGuardDeviceAdmin()
        mockContext = mock(Context::class.java)
    }

    @Test
    fun onDisableRequested_returnsWarningMessage() {
        val intent = mock(Intent::class.java)
        val message = adminReceiver.onDisableRequested(mockContext, intent)

        assertNotNull(message)
        assertTrue(message.toString().contains("60-day"))
    }
}
