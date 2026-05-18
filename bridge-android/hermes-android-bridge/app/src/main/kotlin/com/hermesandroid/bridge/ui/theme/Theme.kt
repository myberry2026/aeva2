package com.hermesandroid.bridge.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Dark Theme Colors (Midnight)
val MidnightBg = Color(0xFF0A0A0B)
val MidnightSurface = Color(0xFF161618)
val MidnightBorder = Color(0xFF2D2D30)
val ElectricBlue = Color(0xFF3B82F6)
val EmeraldGreen = Color(0xFF10B981)
val TextPrimaryDark = Color(0xFFF1F1F1)
val TextSecondaryDark = Color(0xFFA1A1AA)

// Light Theme Colors (Daylight)
val DaylightBg = Color(0xFFF8F9FA)
val DaylightSurface = Color(0xFFFFFFFF)
val DaylightBorder = Color(0xFFE5E7EB)
val SoftBlue = Color(0xFF2563EB)
val SoftGreen = Color(0xFF059669)
val TextPrimaryLight = Color(0xFF111827)
val TextSecondaryLight = Color(0xFF4B5563)

private val DarkColorScheme = darkColorScheme(
    primary = ElectricBlue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFF1E3A8A),
    onPrimaryContainer = Color(0xFFDBEAFE),
    secondary = EmeraldGreen,
    onSecondary = Color.White,
    background = MidnightBg,
    onBackground = TextPrimaryDark,
    surface = MidnightSurface,
    onSurface = TextPrimaryDark,
    surfaceVariant = Color(0xFF1F1F22),
    onSurfaceVariant = TextSecondaryDark,
    outline = MidnightBorder,
    error = Color(0xFFEF4444)
)

private val LightColorScheme = lightColorScheme(
    primary = SoftBlue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDBEAFE),
    onPrimaryContainer = Color(0xFF1E3A8A),
    secondary = SoftGreen,
    onSecondary = Color.White,
    background = DaylightBg,
    onBackground = TextPrimaryLight,
    surface = DaylightSurface,
    onSurface = TextPrimaryLight,
    surfaceVariant = Color(0xFFF3F4F6),
    onSurfaceVariant = TextSecondaryLight,
    outline = DaylightBorder,
    error = Color(0xFFDC2626)
)

@Composable
fun HermesTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
