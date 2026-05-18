package com.hermesandroid.bridge.chat

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.hermesandroid.bridge.chat.ui.ChatMessage
import com.hermesandroid.bridge.chat.ui.ChatMessageText
import com.hermesandroid.bridge.chat.ui.ChatMessageThinking
import com.hermesandroid.bridge.chat.ui.ChatSide
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

data class SavedMessage(
    val side: String, // "USER" or "AGENT"
    val content: String,
    val thinking: String? = null
)

object ChatHistoryRepository {
    private const val FILE_NAME = "chat_history.json"
    private const val TAG = "ChatHistoryRepo"

    suspend fun saveMessages(context: Context, messages: List<ChatMessage>) = withContext(Dispatchers.IO) {
        try {
            val savedList = mutableListOf<SavedMessage>()
            
            var currentThinking: String? = null
            
            for (msg in messages) {
                if (msg is ChatMessageThinking) {
                    currentThinking = msg.content
                } else if (msg is ChatMessageText) {
                    savedList.add(
                        SavedMessage(
                            side = msg.side.name,
                            content = msg.content,
                            thinking = if (msg.side == ChatSide.AGENT) currentThinking else null
                        )
                    )
                    if (msg.side == ChatSide.AGENT) {
                        currentThinking = null
                    }
                }
            }

            val json = Gson().toJson(savedList)
            val file = File(context.filesDir, FILE_NAME)
            file.writeText(json)
            Log.d(TAG, "Saved ${savedList.size} messages to history.")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save history", e)
        }
    }

    suspend fun appendMessage(context: Context, message: ChatMessage) = withContext(Dispatchers.IO) {
        try {
            val messages = loadMessages(context).toMutableList()
            messages.add(message)
            saveMessages(context, messages)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to append message to history", e)
        }
    }

    suspend fun loadMessages(context: Context): List<ChatMessage> = withContext(Dispatchers.IO) {
        try {
            val file = File(context.filesDir, FILE_NAME)
            if (!file.exists()) return@withContext emptyList()

            val json = file.readText()
            val type = object : TypeToken<List<SavedMessage>>() {}.type
            val savedList: List<SavedMessage> = Gson().fromJson(json, type) ?: emptyList()

            val messages = mutableListOf<ChatMessage>()
            for (saved in savedList) {
                val side = if (saved.side == "USER") ChatSide.USER else ChatSide.AGENT
                
                if (saved.thinking != null && side == ChatSide.AGENT) {
                    messages.add(
                        ChatMessageThinking(
                            content = saved.thinking,
                            inProgress = false,
                            side = side
                        )
                    )
                }
                
                messages.add(
                    ChatMessageText(
                        content = saved.content,
                        side = side,
                        isMarkdown = side == ChatSide.AGENT
                    )
                )
            }
            Log.d(TAG, "Loaded ${messages.size} messages from history.")
            return@withContext messages
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load history", e)
            return@withContext emptyList()
        }
    }
}
