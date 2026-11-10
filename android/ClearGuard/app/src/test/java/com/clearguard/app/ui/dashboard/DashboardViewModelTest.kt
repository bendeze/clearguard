package com.clearguard.app.ui.dashboard

import android.content.Context
import com.clearguard.app.data.repository.ProtectionRepositoryImpl
import com.clearguard.app.domain.model.ProtectionStatus
import com.clearguard.app.domain.repository.SecureStorageRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.mockito.Mockito.`when`
import org.mockito.Mockito.mock

@OptIn(ExperimentalCoroutinesApi::class)
class DashboardViewModelTest {

    private val testDispatcher = UnconfinedTestDispatcher()
    private lateinit var repository: ProtectionRepositoryImpl
    private lateinit var mockSecureStorage: SecureStorageRepository
    private lateinit var viewModel: DashboardViewModel
    private lateinit var mockContext: Context

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        repository = ProtectionRepositoryImpl()
        mockSecureStorage = mock(SecureStorageRepository::class.java)
        viewModel = DashboardViewModel(repository, mockSecureStorage)
        mockContext = mock(Context::class.java)
        `when`(mockContext.startService(org.mockito.ArgumentMatchers.any())).thenReturn(null)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun initialUiState_isInactive() {
        assertEquals(ProtectionStatus.INACTIVE, viewModel.uiState.value)
    }

    @Test
    fun startVpnService_updatesUiStateToActive() = runTest {
        viewModel.startVpnService(mockContext)
        assertEquals(ProtectionStatus.ACTIVE, viewModel.uiState.value)
    }

    @Test
    fun stopVpnService_updatesUiStateToInactive() = runTest {
        viewModel.startVpnService(mockContext)
        viewModel.stopVpnService(mockContext)
        assertEquals(ProtectionStatus.INACTIVE, viewModel.uiState.value)
    }

    @Test
    fun isOnboardingCompleted_bothSaved_returnsTrue() = runTest {
        `when`(mockSecureStorage.hasCommitmentPledge()).thenReturn(true)
        `when`(mockSecureStorage.hasPartnerPin()).thenReturn(true)

        assertTrue(viewModel.isOnboardingCompleted())
    }

    @Test
    fun isOnboardingCompleted_missingPartnerPin_returnsFalse() = runTest {
        `when`(mockSecureStorage.hasCommitmentPledge()).thenReturn(true)
        `when`(mockSecureStorage.hasPartnerPin()).thenReturn(false)

        assertFalse(viewModel.isOnboardingCompleted())
    }

    @Test
    fun requestDeactivationWithCoSign_correctCredentials_succeeds() = runTest {
        val pledge = "I pledge clean living"
        val pin = "1234"
        `when`(mockSecureStorage.getCommitmentPledge()).thenReturn(pledge)
        `when`(mockSecureStorage.verifyPartnerPin(pin)).thenReturn(true)

        val result = viewModel.requestDeactivationWithCoSign(pledge, pin)
        assertTrue(result.isSuccess)
    }
}
