package com.clearguard.app.ui.navigation

import android.app.Activity
import android.net.VpnService
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.clearguard.app.domain.model.ProtectionStatus
import com.clearguard.app.ui.auth.LoginScreen
import com.clearguard.app.ui.auth.RegisterEmailScreen
import com.clearguard.app.ui.auth.RegisterPasswordScreen
import com.clearguard.app.ui.auth.RegisterUsernameScreen
import com.clearguard.app.ui.dashboard.DashboardScreen
import com.clearguard.app.ui.dashboard.DashboardViewModel
import com.clearguard.app.ui.onboarding.AccountabilityPartnerEmailScreen
import com.clearguard.app.ui.onboarding.AccountabilityPartnerIntroScreen
import com.clearguard.app.ui.onboarding.AccountabilityPartnerPinScreen
import com.clearguard.app.ui.onboarding.CommitmentPledgeScreen
import com.clearguard.app.ui.onboarding.OnboardingPermissionScreen
import com.clearguard.app.ui.onboarding.OnboardingWelcomeScreen
import com.clearguard.app.ui.settings.SettingsScreen
import com.clearguard.app.ui.settings.SettingsViewModel
import com.clearguard.app.ui.theme.ClearGuardTheme
import kotlinx.coroutines.launch

object Destinations {
    const val DASHBOARD = "dashboard"
    const val SETTINGS = "settings"
    const val ONBOARDING_WELCOME = "onboarding_welcome"
    const val REGISTER_USERNAME = "register_username"
    const val REGISTER_EMAIL = "register_email"
    const val REGISTER_PASSWORD = "register_password"
    const val LOGIN = "login"
    const val ONBOARDING_PERMISSION = "onboarding_permission"
    const val COMMITMENT_PLEDGE = "commitment_pledge"
    const val PARTNER_INTRO = "partner_intro"
    const val PARTNER_PIN = "partner_pin"
    const val PARTNER_EMAIL = "partner_email"
}

@Composable
fun ClearGuardNavGraph(
    navController: NavHostController = rememberNavController()
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val dashboardViewModel: DashboardViewModel = hiltViewModel()
    val settingsViewModel: SettingsViewModel = hiltViewModel()

    val isDarkTheme by settingsViewModel.isDarkTheme.collectAsStateWithLifecycle(initialValue = true)

    var regUsername by remember { mutableStateOf("") }
    var regEmail by remember { mutableStateOf<String?>(null) }

    var isAuthLoading by remember { mutableStateOf(false) }
    var authError by remember { mutableStateOf<String?>(null) }

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

    ClearGuardTheme(darkTheme = isDarkTheme) {
        NavHost(
            navController = navController,
            startDestination = Destinations.DASHBOARD
        ) {
            composable(Destinations.ONBOARDING_WELCOME) {
                OnboardingWelcomeScreen(
                    onContinueClick = {
                        navController.navigate(Destinations.REGISTER_USERNAME)
                    }
                )
            }
            composable(Destinations.REGISTER_USERNAME) {
                RegisterUsernameScreen(
                    onUsernameSubmitted = { username ->
                        regUsername = username
                        navController.navigate(Destinations.REGISTER_EMAIL)
                    },
                    onNavigateToLogin = {
                        authError = null
                        navController.navigate(Destinations.LOGIN)
                    }
                )
            }
            composable(Destinations.REGISTER_EMAIL) {
                RegisterEmailScreen(
                    onEmailSubmitted = { email ->
                        regEmail = email
                        navController.navigate(Destinations.REGISTER_PASSWORD)
                    }
                )
            }
            composable(Destinations.REGISTER_PASSWORD) {
                RegisterPasswordScreen(
                    isLoading = isAuthLoading,
                    errorMessage = authError,
                    onPasswordSubmitted = { password ->
                        scope.launch {
                            isAuthLoading = true
                            authError = null
                            val result = dashboardViewModel.registerUser(regUsername, regEmail, password)
                            isAuthLoading = false
                            if (result.isSuccess) {
                                navController.navigate(Destinations.ONBOARDING_PERMISSION)
                            } else {
                                authError = result.exceptionOrNull()?.message ?: "Account registration failed"
                            }
                        }
                    }
                )
            }
            composable(Destinations.LOGIN) {
                LoginScreen(
                    isLoading = isAuthLoading,
                    errorMessage = authError,
                    onLoginClick = { username, password ->
                        scope.launch {
                            isAuthLoading = true
                            authError = null
                            val result = dashboardViewModel.loginUser(username, password)
                            isAuthLoading = false
                            if (result.isSuccess) {
                                navController.navigate(Destinations.ONBOARDING_PERMISSION)
                            } else {
                                authError = result.exceptionOrNull()?.message ?: "Invalid username or password"
                            }
                        }
                    },
                    onNavigateToRegister = {
                        authError = null
                        navController.navigate(Destinations.REGISTER_USERNAME)
                    }
                )
            }
            composable(Destinations.ONBOARDING_PERMISSION) {
                OnboardingPermissionScreen(
                    onGrantPermissionClick = {
                        requestVpnPermissionAndStart()
                        navController.navigate(Destinations.COMMITMENT_PLEDGE)
                    }
                )
            }
            composable(Destinations.COMMITMENT_PLEDGE) {
                CommitmentPledgeScreen(
                    onPledgeConfirmed = { pledge ->
                        scope.launch {
                            dashboardViewModel.saveCommitmentPledge(pledge)
                            navController.navigate(Destinations.PARTNER_INTRO)
                        }
                    }
                )
            }
            composable(Destinations.PARTNER_INTRO) {
                AccountabilityPartnerIntroScreen(
                    onStartPartnerSetupClick = {
                        navController.navigate(Destinations.PARTNER_PIN)
                    }
                )
            }
            composable(Destinations.PARTNER_PIN) {
                AccountabilityPartnerPinScreen(
                    onPinSubmitted = { pin ->
                        scope.launch {
                            dashboardViewModel.savePartnerPin(pin)
                            navController.navigate(Destinations.PARTNER_EMAIL)
                        }
                    }
                )
            }
            composable(Destinations.PARTNER_EMAIL) {
                AccountabilityPartnerEmailScreen(
                    onEmailSubmitted = { email ->
                        scope.launch {
                            dashboardViewModel.savePartnerEmail(email)
                            requestVpnPermissionAndStart()
                            navController.navigate(Destinations.DASHBOARD) {
                                popUpTo(Destinations.ONBOARDING_WELCOME) { inclusive = true }
                            }
                        }
                    }
                )
            }
            composable(Destinations.DASHBOARD) {
                val status by dashboardViewModel.uiState.collectAsStateWithLifecycle(initialValue = ProtectionStatus.INACTIVE)
                val deactivationDaysRemaining by dashboardViewModel.deactivationDaysRemaining.collectAsStateWithLifecycle(initialValue = null)

                DashboardScreen(
                    status = status,
                    deactivationDaysRemaining = deactivationDaysRemaining,
                    onToggleProtection = {
                        scope.launch {
                            if (status.isProtected) {
                                dashboardViewModel.stopVpnService(context)
                            } else {
                                if (dashboardViewModel.isOnboardingCompleted()) {
                                    requestVpnPermissionAndStart()
                                } else {
                                    navController.navigate(Destinations.ONBOARDING_WELCOME)
                                }
                            }
                        }
                    },
                    onCancelDeactivationRequest = {
                        dashboardViewModel.cancelDeactivationRequest()
                    },
                    onNavigateToSettings = {
                        navController.navigate(Destinations.SETTINGS)
                    }
                )
            }
            composable(Destinations.SETTINGS) {
                val blocklistCount by settingsViewModel.blocklistCount.collectAsStateWithLifecycle(initialValue = 0)

                SettingsScreen(
                    blocklistCount = blocklistCount,
                    isDarkTheme = isDarkTheme,
                    onToggleDarkTheme = { settingsViewModel.toggleDarkTheme(it) },
                    onAccountClick = {
                        navController.navigate(Destinations.REGISTER_USERNAME)
                    },
                    onNavigateBack = {
                        navController.popBackStack()
                    }
                )
            }
        }
    }
}
