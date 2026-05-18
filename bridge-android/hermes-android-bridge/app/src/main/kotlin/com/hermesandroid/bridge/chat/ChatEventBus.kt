package com.hermesandroid.bridge.chat

import com.hermesandroid.bridge.chat.ui.ChatMessage
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow

object ChatEventBus {
    private val _incomingMessages = MutableSharedFlow<ChatMessage>(extraBufferCapacity = 10)
    val incomingMessages = _incomingMessages.asSharedFlow()

    fun emitMessage(message: ChatMessage) {
        _incomingMessages.tryEmit(message)
    }
}
