package com.hermesandroid.bridge.chat.ui

import android.graphics.Bitmap
import androidx.compose.ui.graphics.ImageBitmap

enum class ChatMessageType {
  INFO,
  WARNING,
  ERROR,
  TEXT,
  IMAGE,
  LOADING,
  THINKING,
}

enum class ChatSide {
  USER,
  AGENT,
  SYSTEM,
}

open class ChatMessage(
  open val type: ChatMessageType,
  open val side: ChatSide,
  open val latencyMs: Float = -1f,
  open val accelerator: String = "",
  open val hideSenderLabel: Boolean = false,
  open val disableBubbleShape: Boolean = false,
) {
  open fun clone(): ChatMessage {
    return ChatMessage(
      type = type,
      side = side,
      latencyMs = latencyMs,
      accelerator = accelerator,
      hideSenderLabel = hideSenderLabel,
      disableBubbleShape = disableBubbleShape,
    )
  }
}

class ChatMessageLoading(
  var extraProgressLabel: String = "",
  override val accelerator: String = "",
) : ChatMessage(type = ChatMessageType.LOADING, side = ChatSide.AGENT, accelerator = accelerator) {
  override fun clone(): ChatMessageLoading {
    return ChatMessageLoading(extraProgressLabel = extraProgressLabel, accelerator = accelerator)
  }
}

class ChatMessageInfo(val content: String) :
  ChatMessage(type = ChatMessageType.INFO, side = ChatSide.SYSTEM)

class ChatMessageWarning(val content: String) :
  ChatMessage(type = ChatMessageType.WARNING, side = ChatSide.SYSTEM)

class ChatMessageError(val content: String) :
  ChatMessage(type = ChatMessageType.ERROR, side = ChatSide.SYSTEM)

open class ChatMessageText(
  val content: String,
  override val side: ChatSide,
  override val latencyMs: Float = 0f,
  val isMarkdown: Boolean = true,
  override val accelerator: String = "",
  override val hideSenderLabel: Boolean = false,
  var data: Any? = null,
) :
  ChatMessage(
    type = ChatMessageType.TEXT,
    side = side,
    latencyMs = latencyMs,
    accelerator = accelerator,
    hideSenderLabel = hideSenderLabel,
  ) {
  override fun clone(): ChatMessageText {
    return ChatMessageText(
      content = content,
      side = side,
      latencyMs = latencyMs,
      accelerator = accelerator,
      isMarkdown = isMarkdown,
      hideSenderLabel = hideSenderLabel,
      data = data,
    )
  }
}

class ChatMessageThinking(
  val content: String,
  val inProgress: Boolean,
  override val side: ChatSide = ChatSide.AGENT,
  override val hideSenderLabel: Boolean = false,
  override val accelerator: String = "",
) :
  ChatMessage(
    type = ChatMessageType.THINKING,
    side = side,
    hideSenderLabel = hideSenderLabel,
    disableBubbleShape = true,
    accelerator = accelerator,
  ) {
  override fun clone(): ChatMessageThinking {
    return ChatMessageThinking(
      content = content,
      inProgress = inProgress,
      side = side,
      hideSenderLabel = hideSenderLabel,
      accelerator = accelerator,
    )
  }
}