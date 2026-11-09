package com.clearguard.app.ui.navigation

import android.app.Activity
import android.net.VpnService
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalContext
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.clearguard.app.domain.model.ProtectionStatus
import com.clearguard.app.ui.dashboard.DashboardScreen
import com.clearguard.app.ui.dashboard.DashboardViewModel
import com.clearguard.app.ui.onboarding.OnboardingScreen
import com.clearguard.app.ui.settings.SettingsScreen
import com.clearguard.app.ui.settings.SettingsViewModel

object Destinations {
    const val DASHBOARD = "dashboard"
    const val SETTINGS = "settings"
    const val ONBOARDING = "onboarding"
}

@Composable
fun ClearGuardNavGraph(
    navController: NavHostController = rememberNavController()
) {
    val context = LocalContext.current
    val dashboardViewModel: DashboardViewModel = hiltViewModel()

    val vpnPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            dashboardViewModel.startVpnService(context)
        }
    }

    val requestVpnPermissionAndStart = {
        val prepareIntent = VpnService.prepare(context)
        if (prepareIntent != null) {
            vpnPermissionLauncher.launch(prepareIntent)
        } else {
            dashboardViewModel.startVpnService(context)
        }
    }

    NavHost(
        navController = navController,
        startDestination = Destinations.DASHBOARD
    ) {
        composable(Destinations.ONBOARDING) {
            OnboardingScreen(
                onGrantPermissionClick = {
                    requestVpnPermissionAndStart()
                    navController.navigate(Destinations.DASHBOARD) {
                        popUpTo(Destinations.ONBOARDING) { inclusive = true }
                    }
                }
            )
        }
        composable(Destinations.DASHBOARD) {
            val status by dashboardViewModel.uiState.collectAsStateWithLifecycle(initialValue = ProtectionStatus.INACTIVE)

            DashboardScreen(
                status = status,
                onToggleProtection = {
                    if (status.isProtected) {
                        dashboardViewModel.stopVpnService(context)
                    } else {
                        requestVpnPermissionAndStart()
                    }
                },
                onNavigateToSettings = {
                    navController.navigate(Destinations.SETTINGS)
                }
            )
        }
        composable(Destinations.SETTINGS) {
            val settingsViewModel: SettingsViewModel = hiltViewModel()
            val blocklistCount by settingsViewModel.blocklistCount.collectAsStateWithLifecycle(initialValue = 0)

            SettingsScreen(
                blocklistCount = blocklistCount,
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }
    }
}
