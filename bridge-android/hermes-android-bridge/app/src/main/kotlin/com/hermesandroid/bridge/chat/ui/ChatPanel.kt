package com.hermesandroid.bridge.chat.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
fun ChatPanel(
    messages: List<ChatMessage>,
    onSendMessage: (String) -> Unit,
    isGenerating: Boolean = false,
    onStopGeneration: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val listState = rememberLazyListState()

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Column(modifier = modifier.fillMaxSize().imePadding()) {
        LazyColumn(
            state = listState,
            modifier = Modifier.weight(1f),
            contentPadding = PaddingValues(horizontal = 0.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            items(messages) { message ->
                MessageRow(message = message)
            }
        }
        MessageInputText(
            onSendMessage = onSendMessage,
            isGenerating = isGenerating,
            onStopGeneration = onStopGeneration
        )
    }
}

@Composable
fun MessageRow(message: ChatMessage) {
    val isUser = message.side == ChatSide.USER
    val alignment = if (isUser) Alignment.End else Alignment.Start
    
    val bubbleColor = if (isUser) {
        MaterialTheme.colorScheme.primary
    } else {
        MaterialTheme.colorScheme.surfaceVariant
    }
    
    val borderColor = if (isUser) Color.Transparent else MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
    
    val hardCornerAtLeftOrRight = !isUser 
    val extraPaddingStart = if (isUser) 60.dp else 0.dp
    val extraPaddingEnd = if (isUser) 0.dp else 60.dp

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 12.dp + extraPaddingStart, end = 12.dp + extraPaddingEnd),
        horizontalAlignment = alignment
    ) {
        if (!message.hideSenderLabel) {
            MessageSender(message = message)
            Spacer(modifier = Modifier.height(2.dp))
        }

        Box(
            modifier = Modifier
                .clip(MessageBubbleShape(radius = 18.dp, hardCornerAtLeftOrRight = hardCornerAtLeftOrRight))
                .background(bubbleColor)
                .then(
                    if (!isUser) Modifier.border(
                        width = 1.dp,
                        color = borderColor,
                        shape = MessageBubbleShape(radius = 18.dp, hardCornerAtLeftOrRight = hardCornerAtLeftOrRight)
                    ) else Modifier
                )
        ) {
            when (message) {
                is ChatMessageText -> {
                    MessageBodyText(message = message, inProgress = message.data == "streaming")
                }
                is ChatMessageThinking -> {
                    MessageBodyThinking(content = message.content, inProgress = message.inProgress, side = message.side)
                }
                is ChatMessageLoading -> {
                    MessageBodyLoading(message = message)
                }
                is ChatMessageError -> {
                    MessageBodyError(message = message)
                }
                else -> {
                    Text(text = "Unsupported message", modifier = Modifier.padding(12.dp))
                }
            }
        }
        
        if (message.side == ChatSide.AGENT && message.latencyMs > 0) {
            Spacer(modifier = Modifier.height(4.dp))
            LatencyText(message = message)
        }
    }
}
