package com.clearguard.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.clearguard.app.ui.dashboard.DashboardScreen
import com.clearguard.app.ui.settings.SettingsScreen

object Destinations {
    const val DASHBOARD = "dashboard"
    const val SETTINGS = "settings"
}

@Composable
fun ClearGuardNavGraph(
    navController: NavHostController = rememberNavController()
) {
    NavHost(
        navController = navController,
        startDestination = Destinations.DASHBOARD
    ) {
        composable(Destinations.DASHBOARD) {
            DashboardScreen(
                onNavigateToSettings = {
                    navController.navigate(Destinations.SETTINGS)
                }
            )
        }
        composable(Destinations.SETTINGS) {
            SettingsScreen(
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }
    }
}
