package com.hermesandroid.bridge.chat

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.LightMode
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import com.hermesandroid.bridge.SettingsActivity
import com.hermesandroid.bridge.chat.ui.ChatPanel
import com.hermesandroid.bridge.ui.theme.HermesTheme
import com.hermesandroid.bridge.ui.theme.ThemeManager

class ChatActivity : ComponentActivity() {
    private val viewModel: ChatViewModel by viewModels()

    @OptIn(ExperimentalMaterial3Api::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val isDarkMode by ThemeManager.isDarkMode.collectAsState()
            HermesTheme(darkTheme = isDarkMode) {
                val messages by viewModel.messages.collectAsState()
                val isGenerating by viewModel.isGenerating.collectAsState()

                Scaffold(
                    topBar = {
                        TopAppBar(
                            title = { Text("Aeva", fontWeight = FontWeight.Bold) },
                            actions = {
                                IconButton(onClick = {
                                    ThemeManager.setDarkMode(!isDarkMode)
                                }) {
                                    Icon(
                                        if (isDarkMode) Icons.Filled.LightMode else Icons.Filled.DarkMode,
                                        contentDescription = "Toggle Theme"
                                    )
                                }
                                IconButton(onClick = {
                                    viewModel.clearHistory()
                                }) {
                                    Icon(Icons.Filled.DeleteOutline, contentDescription = "Clear chat")
                                }
                                IconButton(onClick = {
                                    startActivity(Intent(this@ChatActivity, SettingsActivity::class.java))
                                }) {
                                    Icon(Icons.Filled.Settings, contentDescription = "Settings")
                                }
                            },
                            colors = TopAppBarDefaults.topAppBarColors(
                                containerColor = MaterialTheme.colorScheme.background,
                                titleContentColor = MaterialTheme.colorScheme.onBackground,
                                actionIconContentColor = MaterialTheme.colorScheme.onBackground
                            )
                        )
                    }
                ) { innerPadding ->
                    Surface(modifier = Modifier.padding(innerPadding).fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                        ChatPanel(
                            messages = messages,
                            onSendMessage = { text ->
                                viewModel.sendMessage(text)
                            },
                            isGenerating = isGenerating,
                            onStopGeneration = {
                                viewModel.stopGeneration()
                            }
                        )
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        if (android.provider.Settings.canDrawOverlays(this)) {
            com.hermesandroid.bridge.overlay.StatusOverlay.show(this)
        }
    }
}
