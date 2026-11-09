package com.clearguard.app.service.receiver

import android.content.Context
import android.content.Intent
import com.clearguard.app.data.repository.ProtectionRepositoryImpl
import com.clearguard.app.domain.model.ProtectionStatus
import dagger.hilt.internal.GeneratedComponentManager
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Test
import org.mockito.ArgumentCaptor
import org.mockito.Mockito.`when`
import org.mockito.Mockito.mock
import org.mockito.Mockito.verify

abstract class TestHiltApplication : android.app.Application(), GeneratedComponentManager<Any>

@OptIn(ExperimentalCoroutinesApi::class)
class BootReceiverTest {

    private val testDispatcher = UnconfinedTestDispatcher()
    private lateinit var receiver: BootReceiver
    private lateinit var mockContext: Context
    private lateinit var mockHiltApp: TestHiltApplication
    private lateinit var mockInjector: BootReceiver_GeneratedInjector
    private lateinit var fakeRepository: ProtectionRepositoryImpl

    @Before
    fun setUp() {
        receiver = BootReceiver(testDispatcher)
        mockContext = mock(Context::class.java)
        mockHiltApp = mock(TestHiltApplication::class.java)
        mockInjector = mock(BootReceiver_GeneratedInjector::class.java)

        `when`(mockContext.applicationContext).thenReturn(mockHiltApp)
        `when`(mockHiltApp.generatedComponent()).thenReturn(mockInjector)

        fakeRepository = ProtectionRepositoryImpl()
        receiver.protectionRepository = fakeRepository
    }

    @Test
    fun onReceive_bootCompletedAndActive_triggersVpnStartService() = runTest {
        fakeRepository.setProtectionStatus(ProtectionStatus.ACTIVE)

        val mockIntent = mock(Intent::class.java)
        `when`(mockIntent.action).thenReturn(Intent.ACTION_BOOT_COMPLETED)

        receiver.onReceive(mockContext, mockIntent)

        val captor = ArgumentCaptor.forClass(Intent::class.java)
        verify(mockContext).startService(captor.capture())

        assertNotNull(captor.value)
    }
}
