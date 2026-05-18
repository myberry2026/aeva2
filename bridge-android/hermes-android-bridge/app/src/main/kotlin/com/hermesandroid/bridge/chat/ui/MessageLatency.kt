package com.hermesandroid.bridge.chat.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@Composable
fun LatencyText(message: ChatMessage, modifier: Modifier = Modifier) {
  if (message.latencyMs > 0) {
    val durationStr = String.format("%.1f s", message.latencyMs / 1000f)
    Text(
      text = durationStr,
      style = MaterialTheme.typography.labelSmall,
      color = MaterialTheme.colorScheme.onSurfaceVariant,
      modifier = modifier
    )
  }
}
