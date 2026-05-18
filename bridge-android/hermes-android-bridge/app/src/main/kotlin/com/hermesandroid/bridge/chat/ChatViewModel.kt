package com.hermesandroid.bridge.chat

import com.hermesandroid.bridge.R

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.hermesandroid.bridge.chat.ui.ChatMessage
import com.hermesandroid.bridge.chat.ui.ChatMessageError
import com.hermesandroid.bridge.chat.ui.ChatMessageLoading
import com.hermesandroid.bridge.chat.ui.ChatMessageText
import com.hermesandroid.bridge.chat.ui.ChatMessageThinking
import com.hermesandroid.bridge.chat.ui.ChatSide
import com.google.ai.edge.litertlm.Contents
import com.hermesandroid.bridge.llm.LlmInferenceManager
import com.hermesandroid.bridge.overlay.StatusOverlay
import com.hermesandroid.bridge.executor.ActionExecutor
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody

class ChatViewModel(application: Application) : AndroidViewModel(application) {
    companion object {
        private const val TAG = "ChatViewModel"
    }

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages.asStateFlow()

    private val _isGenerating = MutableStateFlow(false)
    val isGenerating: StateFlow<Boolean> = _isGenerating.asStateFlow()

    private var inferenceJob: Job? = null

    init {
        viewModelScope.launch {
            val loaded = ChatHistoryRepository.loadMessages(getApplication())
            Log.d(TAG, "init: Loaded ${loaded.size} messages from history")
            _messages.value = loaded
        }
        viewModelScope.launch {
            ChatEventBus.incomingMessages.collect { msg ->
                Log.d(TAG, "ChatEventBus received: $msg")
                val currentList = _messages.value.toMutableList()
                currentList.add(msg)
                _messages.value = currentList
                saveHistory()
            }
        }
    }

    fun sendMessage(text: String) {
        if (text.isBlank()) return
        if (_isGenerating.value) {
            Log.w(TAG, "sendMessage: Already generating, ignoring input")
            return
        }

        Log.i(TAG, "sendMessage: User sent '${text.take(50)}...' (${text.length} chars)")

        // UI-Driven Agent: Route to Termux relay via simple HTTP POST
        val isTaskMode = text.trim().startsWith("/task", ignoreCase = true) || text.trim().startsWith("/agent", ignoreCase = true)
        
        if (isTaskMode) {
            val goalText = text.replaceFirst(Regex("^(/task|/agent)\\s*", RegexOption.IGNORE_CASE), "")
            val userMsg = ChatMessageText(content = text, side = ChatSide.USER, isMarkdown = false)
            val currentList = _messages.value.toMutableList()
            currentList.add(userMsg)
            _messages.value = currentList
            StatusOverlay.setTouchable(false)
            StatusOverlay.updateDashboard(StatusOverlay.DashboardState(
                goal = goalText,
                status = "STARTING"
            ))

            viewModelScope.launch {
                try {
                    val client = okhttp3.OkHttpClient.Builder()
                        .connectTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
                        .readTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
                        .build()
                    val json = org.json.JSONObject().put("text", goalText).toString()
                    val mediaType = "application/json".toMediaType()
                    val body = json.toRequestBody(mediaType)
                    val request = okhttp3.Request.Builder()
                        .url("http://127.0.0.1:8767/task")
                        .post(body)
                        .build()
                    
                    val (ok, respBody) = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                        client.newCall(request).execute().use { resp ->
                            resp.isSuccessful to (resp.body?.string() ?: "{}")
                        }
                    }
                    Log.i(TAG, "Relay /task response: $respBody (ok=$ok)")
                    
                    val newList = _messages.value.toMutableList()
                    if (ok) {
                        newList.add(ChatMessageText(
                            content = getApplication<Application>().getString(R.string.agent_received_task, goalText),
                            side = ChatSide.AGENT,
                            isMarkdown = true
                        ))
                    } else {
                        newList.add(ChatMessageText(
                            content = getApplication<Application>().getString(R.string.task_submission_failed, respBody),
                            side = ChatSide.AGENT,
                            isMarkdown = true
                        ))
                    }
                    _messages.value = newList
                    saveHistory()
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to POST /task: ${e.message}", e)
                    val newList = _messages.value.toMutableList()
                    newList.add(ChatMessageText(
                        content = getApplication<Application>().getString(R.string.cannot_connect_relay, e.message),
                        side = ChatSide.AGENT,
                        isMarkdown = true
                    ))
                    _messages.value = newList
                    saveHistory()
                }
            }
            return
        }

        val isStopMode = text.trim().equals("/stop", ignoreCase = true)
        if (isStopMode) {
            val userMsg = ChatMessageText(content = text, side = ChatSide.USER, isMarkdown = false)
            val currentList = _messages.value.toMutableList()
            currentList.add(userMsg)
            _messages.value = currentList

            viewModelScope.launch {
                try {
                    val client = okhttp3.OkHttpClient.Builder()
                        .connectTimeout(5, java.util.concurrent.TimeUnit.SECONDS)
                        .readTimeout(5, java.util.concurrent.TimeUnit.SECONDS)
                        .build()
                    val request = okhttp3.Request.Builder()
                        .url("http://127.0.0.1:8767/stop")
                        .post("".toRequestBody("application/json".toMediaType()))
                        .build()
                    val respBody = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                        client.newCall(request).execute().use { resp ->
                            resp.body?.string() ?: "{}"
                        }
                    }
                    Log.i(TAG, "Relay /stop response: $respBody")
                    StatusOverlay.setTouchable(true)
                    StatusOverlay.updateMessage(getApplication<Application>().getString(R.string.agent_stopped_voice))
                    val speakResult = ActionExecutor.speak(getApplication<Application>().getString(R.string.agent_stopped_tts), android.speech.tts.TextToSpeech.QUEUE_FLUSH)
                    Log.i(TAG, "speak('Agent stopped') -> success=${speakResult.success}, msg=${speakResult.message}")
                    val newList = _messages.value.toMutableList()
                    newList.add(ChatMessageText(
                        content = getApplication<Application>().getString(R.string.agent_stopped),
                        side = ChatSide.AGENT,
                        isMarkdown = true
                    ))
                    _messages.value = newList
                    saveHistory()
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to POST /stop: ${e.message}", e)
                    val newList = _messages.value.toMutableList()
                    newList.add(ChatMessageText(
                        content = getApplication<Application>().getString(R.string.cannot_connect_relay_simple, e.message),
                        side = ChatSide.AGENT,
                        isMarkdown = true
                    ))
                    _messages.value = newList
                    saveHistory()
                }
            }
            return
        }

        val userMsg = ChatMessageText(
            content = text,
            side = ChatSide.USER,
            isMarkdown = false
        )

        val currentList = _messages.value.toMutableList()
        currentList.add(userMsg)
        currentList.add(ChatMessageLoading())
        _messages.value = currentList
        saveHistory()

        _isGenerating.value = true
        val startTime = System.currentTimeMillis()

        inferenceJob = viewModelScope.launch {
            if (!LlmInferenceManager.isLoaded) {
                Log.e(TAG, "sendMessage: Model not loaded!")
                removeLoadingAndAddError("Model is not loaded. Please go to Settings ⚙️ to load the model first.")
                _isGenerating.value = false
                return@launch
            }

            // Build conversation history (exclude the just-sent message)
            val history = _messages.value
                .filterIsInstance<ChatMessageText>()
                .filter { it != userMsg }
                .map {
                    val role = if (it.side == ChatSide.USER) "user" else "assistant"
                    Pair(role, it.content)
                }
            Log.d(TAG, "sendMessage: Sending with ${history.size} history messages")

            try {
                val responseBuilder = StringBuilder()
                var thinkingBuilder = StringBuilder()

                // Use streaming inference for real-time text display
                LlmInferenceManager.inferStreaming(
                    systemPrompt = "You are Aeva, a helpful AI assistant running entirely on-device.",
                    initialMessages = history,
                    prompt = Contents.of(text)
                ).collect { partial ->
                    if (partial.error != null && partial.text == null) {
                        Log.e(TAG, "Streaming error: ${partial.error}")
                        removeLoadingAndAddError("Error: ${partial.error}")
                        _isGenerating.value = false
                        return@collect
                    }

                    // Accumulate text
                    if (partial.text != null) {
                        responseBuilder.append(partial.text)
                    }
                    if (partial.thinking != null) {
                        thinkingBuilder.append(partial.thinking)
                    }

                    // Update UI with streaming content
                    val newList = _messages.value.toMutableList()
                    newList.removeAll { it is ChatMessageLoading }
                    // Remove previous streaming messages (thinking + text)
                    newList.removeAll { it is ChatMessageThinking && it.inProgress }
                    newList.removeAll { it is ChatMessageText && it.side == ChatSide.AGENT && it.data == "streaming" }

                    if (thinkingBuilder.isNotBlank()) {
                        newList.add(
                            ChatMessageThinking(
                                content = thinkingBuilder.toString(),
                                inProgress = true,
                                side = ChatSide.AGENT
                            )
                        )
                    }
                    if (responseBuilder.isNotBlank()) {
                        newList.add(
                            ChatMessageText(
                                content = responseBuilder.toString(),
                                side = ChatSide.AGENT,
                                isMarkdown = true,
                                data = "streaming"  // marker for streaming messages
                            )
                        )
                    }
                    _messages.value = newList
                }

                // Streaming done — finalize messages
                val elapsed = System.currentTimeMillis() - startTime
                Log.i(TAG, "sendMessage: Inference completed in ${elapsed}ms, response: ${responseBuilder.length} chars")

                val finalList = _messages.value.toMutableList()
                finalList.removeAll { it is ChatMessageLoading }
                finalList.removeAll { it is ChatMessageThinking && it.inProgress }
                finalList.removeAll { it is ChatMessageText && it.side == ChatSide.AGENT && it.data == "streaming" }

                if (thinkingBuilder.isNotBlank()) {
                    finalList.add(
                        ChatMessageThinking(
                            content = thinkingBuilder.toString(),
                            inProgress = false,
                            side = ChatSide.AGENT
                        )
                    )
                }
                if (responseBuilder.isNotBlank()) {
                    finalList.add(
                        ChatMessageText(
                            content = responseBuilder.toString(),
                            side = ChatSide.AGENT,
                            isMarkdown = true,
                            latencyMs = elapsed.toFloat()
                        )
                    )
                }
                _messages.value = finalList
                saveHistory()
            } catch (e: kotlinx.coroutines.CancellationException) {
                Log.i(TAG, "sendMessage: Generation cancelled by user")
                val finalList = _messages.value.toMutableList()
                finalList.removeAll { it is ChatMessageLoading }

                // Finalize thinking state
                val thinkingIndex = finalList.indexOfFirst { it is ChatMessageThinking && it.inProgress }
                if (thinkingIndex != -1) {
                    val msg = finalList[thinkingIndex] as ChatMessageThinking
                    finalList[thinkingIndex] = ChatMessageThinking(
                        content = msg.content,
                        inProgress = false,
                        side = msg.side,
                        hideSenderLabel = msg.hideSenderLabel,
                        accelerator = msg.accelerator
                    )
                }

                // Finalize streaming text state
                val textIndex = finalList.indexOfFirst { it is ChatMessageText && it.data == "streaming" }
                if (textIndex != -1) {
                    val msg = finalList[textIndex] as ChatMessageText
                    finalList[textIndex] = ChatMessageText(
                        content = msg.content,
                        side = msg.side,
                        latencyMs = msg.latencyMs,
                        isMarkdown = msg.isMarkdown,
                        accelerator = msg.accelerator,
                        hideSenderLabel = msg.hideSenderLabel,
                        data = null // remove streaming marker
                    )
                }

                _messages.value = finalList
                saveHistory()
            } catch (e: Exception) {
                Log.e(TAG, "sendMessage: Exception during inference", e)
                removeLoadingAndAddError("Exception: ${e.message}")
            }
            _isGenerating.value = false
        }
    }

    fun stopGeneration() {
        Log.i(TAG, "stopGeneration: User requested stop")
        LlmInferenceManager.stopInference()
        inferenceJob?.cancel()
        _isGenerating.value = false
    }

    fun clearHistory() {
        Log.i(TAG, "clearHistory: Clearing all messages")
        _messages.value = emptyList()
        saveHistory()
    }

    private fun removeLoadingAndAddError(errorText: String) {
        val newList = _messages.value.toMutableList()
        newList.removeAll { it is ChatMessageLoading }
        newList.add(ChatMessageError(errorText))
        _messages.value = newList
        saveHistory()
    }

    private fun saveHistory() {
        viewModelScope.launch {
            ChatHistoryRepository.saveMessages(getApplication(), _messages.value)
        }
    }
}
