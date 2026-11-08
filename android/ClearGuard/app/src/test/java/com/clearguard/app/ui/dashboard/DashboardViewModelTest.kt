package com.clearguard.app.ui.dashboard

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

@OptIn(ExperimentalCoroutinesApi::class)
class DashboardViewModelTest {

    private val testDispatcher = UnconfinedTestDispatcher()
    private lateinit var repository: ProtectionRepositoryImpl
    private lateinit var viewModel: DashboardViewModel

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        repository = ProtectionRepositoryImpl()
        viewModel = DashboardViewModel(repository)
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
    fun toggleProtection_updatesUiStateToActive() = runTest {
        viewModel.toggleProtection()
        assertEquals(ProtectionStatus.ACTIVE, viewModel.uiState.value)
    }
}
