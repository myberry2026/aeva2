package com.hermesandroid.bridge.chat.ui

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.hermesandroid.bridge.voice.VoiceManager

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MessageInputText(
    onSendMessage: (String) -> Unit,
    isGenerating: Boolean = false,
    onStopGeneration: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var text by remember { mutableStateOf("") }
    var isListening by remember { mutableStateOf(false) }
    val accumulated = remember { StringBuilder() }

    // Permission
    var audioPermissionGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
                    PackageManager.PERMISSION_GRANTED
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        audioPermissionGranted = granted
        if (granted) {
            isListening = true
            accumulated.clear()
            VoiceManager.startListening(context, voiceCallback(
                onText = { result ->
                    if (accumulated.isNotEmpty()) accumulated.append(" ")
                    accumulated.append(result)
                    text = accumulated.toString()
                },
                onError = { isListening = false }
            ), continuous = true)
        }
    }

    fun toggleVoice() {
        if (isListening) {
            VoiceManager.stopListening()
            isListening = false
        } else {
            if (audioPermissionGranted) {
                isListening = true
                accumulated.clear()
                VoiceManager.startListening(context, voiceCallback(
                    onText = { result ->
                        if (accumulated.isNotEmpty()) accumulated.append(" ")
                        accumulated.append(result)
                        text = accumulated.toString()
                    },
                    onError = { isListening = false }
                ), continuous = true)
            } else {
                permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            }
        }
    }

    Surface(
        modifier = modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.background,
    ) {
        Row(
            modifier = Modifier
                .padding(start = 12.dp, end = 12.dp, top = 8.dp, bottom = 20.dp)
                .navigationBarsPadding(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = text,
                onValueChange = { text = it },
                modifier = Modifier.weight(1f),
                placeholder = {
                    Text(
                        if (isListening) "Listening..." else "Message Aeva...",
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                    )
                },
                shape = androidx.compose.foundation.shape.RoundedCornerShape(28.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = MaterialTheme.colorScheme.surface,
                    unfocusedContainerColor = MaterialTheme.colorScheme.surface,
                    focusedBorderColor = if (isListening)
                        MaterialTheme.colorScheme.primary
                    else
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.5f),
                    unfocusedBorderColor = if (isListening)
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.7f)
                    else
                        MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)
                ),
                maxLines = 5,
                enabled = !isGenerating
            )

            Spacer(modifier = Modifier.width(8.dp))

            // Mic toggle
            IconButton(
                onClick = { toggleVoice() },
                enabled = !isGenerating
            ) {
                Icon(
                    if (isListening) Icons.Filled.Stop else Icons.Filled.Mic,
                    contentDescription = if (isListening) "Stop" else "Voice",
                    tint = if (isListening)
                        MaterialTheme.colorScheme.error
                    else
                        MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Send / Stop generation
            if (isGenerating) {
                FilledIconButton(
                    onClick = onStopGeneration,
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = MaterialTheme.colorScheme.errorContainer,
                        contentColor = MaterialTheme.colorScheme.onErrorContainer
                    )
                ) {
                    Icon(Icons.Filled.Stop, contentDescription = "Stop")
                }
            } else {
                FilledIconButton(
                    onClick = {
                        if (text.isNotBlank()) {
                            onSendMessage(text)
                            text = ""
                        }
                    },
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary
                    ),
                    enabled = text.isNotBlank()
                ) {
                    Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send")
                }
            }
        }
    }
}

private fun voiceCallback(
    onText: (String) -> Unit,
    onError: () -> Unit
): VoiceManager.VoiceCallback = object : VoiceManager.VoiceCallback {
    override fun onPartialResult(partial: String) {}
    override fun onFinalResult(result: String) {
        if (result.isNotBlank()) onText(result)
    }
    override fun onError(err: String) { onError() }
}
