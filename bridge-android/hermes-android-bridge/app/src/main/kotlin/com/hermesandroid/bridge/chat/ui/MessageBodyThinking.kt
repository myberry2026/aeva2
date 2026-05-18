package com.hermesandroid.bridge.chat.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun MessageBodyThinking(content: String, inProgress: Boolean, side: ChatSide) {
    val textColor = if (side == ChatSide.USER) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant
    Column(modifier = Modifier.padding(12.dp)) {
        Text(
            text = if (inProgress) "🤔 Thinking..." else "🤔 Thought Process", 
            style = MaterialTheme.typography.labelSmall, 
            color = textColor.copy(alpha = 0.7f)
        )
        Text(
            text = content, 
            color = textColor.copy(alpha = 0.8f), 
            style = MaterialTheme.typography.bodySmall
        )
    }
}
