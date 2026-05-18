package com.hermesandroid.bridge.chat.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun MessageSender(
  message: ChatMessage,
  agentName: String = "Aeva",
  imageHistoryCurIndex: Int = 0,
) {
  Row(
    verticalAlignment = Alignment.CenterVertically,
    horizontalArrangement = Arrangement.spacedBy(8.dp)
  ) {
    if (message.side == ChatSide.AGENT) {
      Icon(
        imageVector = Icons.Default.SmartToy,
        contentDescription = "Agent",
        tint = MaterialTheme.colorScheme.primary,
        modifier = Modifier.size(16.dp)
      )
      Text(
        text = agentName,
        style = MaterialTheme.typography.labelMedium,
        fontWeight = FontWeight.Bold,
        color = MaterialTheme.colorScheme.primary
      )
    } else if (message.side == ChatSide.USER) {
      Text(
        text = "You",
        style = MaterialTheme.typography.labelMedium,
        fontWeight = FontWeight.Bold,
        color = MaterialTheme.colorScheme.secondary
      )
      Icon(
        imageVector = Icons.Default.Person,
        contentDescription = "User",
        tint = MaterialTheme.colorScheme.secondary,
        modifier = Modifier.size(16.dp)
      )
    }
  }
}
