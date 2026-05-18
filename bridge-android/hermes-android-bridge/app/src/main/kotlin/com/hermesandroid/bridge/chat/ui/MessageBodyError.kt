package com.hermesandroid.bridge.chat.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun MessageBodyError(message: ChatMessageError) {
    Text(
        text = message.content, 
        modifier = Modifier.padding(12.dp),
        color = MaterialTheme.colorScheme.error
    )
}
