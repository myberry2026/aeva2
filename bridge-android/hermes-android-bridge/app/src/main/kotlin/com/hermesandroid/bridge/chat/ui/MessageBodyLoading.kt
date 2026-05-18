package com.hermesandroid.bridge.chat.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun MessageBodyLoading(message: ChatMessageLoading) {
    CircularProgressIndicator(
        modifier = Modifier.padding(12.dp).size(24.dp), 
        color = MaterialTheme.colorScheme.onSurfaceVariant, 
        strokeWidth = 2.dp
    )
}
