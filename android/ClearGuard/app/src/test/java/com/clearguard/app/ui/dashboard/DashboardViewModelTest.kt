package com.clearguard.app.ui.dashboard

import android.content.Context
import com.clearguard.app.data.repository.ProtectionRepositoryImpl
import com.clearguard.app.domain.model.ProtectionStatus
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test
import org.mockito.Mockito.`when`
import org.mockito.Mockito.mock

@OptIn(ExperimentalCoroutinesApi::class)
class DashboardViewModelTest {

    private val testDispatcher = UnconfinedTestDispatcher()
    private lateinit var repository: ProtectionRepositoryImpl
    private lateinit var viewModel: DashboardViewModel
    private lateinit var mockContext: Context

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        repository = ProtectionRepositoryImpl()
        viewModel = DashboardViewModel(repository)
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
}
