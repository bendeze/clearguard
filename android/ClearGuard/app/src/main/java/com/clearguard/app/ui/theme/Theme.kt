package com.clearguard.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val DarkColorScheme = darkColorScheme(
    primary = MonoWhite,
    onPrimary = MonoBlack,
    primaryContainer = MonoGray700,
    onPrimaryContainer = MonoWhite,
    secondary = MonoGray200,
    onSecondary = MonoBlack,
    background = MonoBlack,
    onBackground = MonoWhite,
    surface = MonoGray900,
    onSurface = MonoWhite,
    surfaceVariant = MonoGray800,
    onSurfaceVariant = MonoGray500,
    outline = OutlineDark,
    outlineVariant = OutlineVariantDark
)

private val LightColorScheme = lightColorScheme(
    primary = MonoBlack,
    onPrimary = MonoWhite,
    primaryContainer = MonoGray200,
    onPrimaryContainer = MonoBlack,
    secondary = MonoGray700,
    onSecondary = MonoWhite,
    background = MonoWhite,
    onBackground = MonoBlack,
    surface = MonoWhite,
    onSurface = MonoBlack,
    surfaceVariant = MonoGray100,
    onSurfaceVariant = MonoGray500,
    outline = MonoGray300,
    outlineVariant = MonoGray200
)

@Composable
fun ClearGuardTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
