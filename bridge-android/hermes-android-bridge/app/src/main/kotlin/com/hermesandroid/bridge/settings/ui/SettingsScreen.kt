package com.hermesandroid.bridge.settings.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    // Status
    a11yActive: Boolean,
    serverPort: String, // e.g. "8765" or "stopped"
    serverRunning: Boolean,
    relayStatus: String,
    relayConnected: Boolean,
    authCode: String,
    
    // Permissions
    a11yPermissionGranted: Boolean,
    overlayPermissionGranted: Boolean,
    screenRecordGranted: Boolean,
    
    // LLM
    llmServerPort: String,
    llmServerRunning: Boolean,
    modelStatus: String,
    modelLoaded: Boolean,
    modelReady: Boolean,
    modelName: String,
    downloadProgress: Float?, // 0.0 to 1.0, null if not downloading
    downloadLabel: String,
    
    // Connection
    serverUrl: String,
    localAddress: String,
    
    // Actions
    onBack: () -> Unit,
    onToggleA11y: (Boolean) -> Unit,
    onToggleOverlay: (Boolean) -> Unit,
    onToggleScreenRecord: (Boolean) -> Unit,
    onToggleMainServer: () -> Unit,
    onToggleLlmServer: () -> Unit,
    onModelAction: () -> Unit, // Download/Load/Reload/Pause
    onRegenerateCode: () -> Unit,
    onCopyCode: () -> Unit,
    onUrlChange: (String) -> Unit,
    onConnect: () -> Unit,
    onDisconnect: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Version info
            Text(
                text = "v0.2.0",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.outline,
                modifier = Modifier.align(Alignment.End)
            )

            // Status Section
            SettingsCard(title = "Status") {
                StatusItem(label = "a11y", status = if (a11yActive) "active" else "inactive", isActive = a11yActive)
                StatusItem(
                    label = "bridge-server", 
                    status = serverPort, 
                    isActive = serverRunning,
                    action = {
                        Button(
                            onClick = onToggleMainServer,
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
                            modifier = Modifier.height(32.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (serverRunning) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.primaryContainer,
                                contentColor = if (serverRunning) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onPrimaryContainer
                            )
                        ) {
                            Text(if (serverRunning) "STOP" else "START", fontSize = 12.sp)
                        }
                    }
                )
                StatusItem(label = "relay", status = relayStatus, isActive = relayConnected)
                StatusItem(label = "auth", status = authCode, isActive = authCode != "------")
            }

            // Permissions Section
            SettingsCard(title = "Permissions") {
                PermissionItem(
                    label = "Accessibility Service",
                    description = "Required for UI interaction",
                    checked = a11yPermissionGranted,
                    onCheckedChange = onToggleA11y
                )
                PermissionItem(
                    label = "Status Overlay",
                    description = "Show status bubble over apps",
                    checked = overlayPermissionGranted,
                    onCheckedChange = onToggleOverlay
                )
                PermissionItem(
                    label = "Screen Recording",
                    description = "Required for screen reading",
                    checked = screenRecordGranted,
                    onCheckedChange = onToggleScreenRecord
                )
            }

            // Pairing Code Section
            SettingsCard(title = "Pairing Code") {
                Column(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = authCode,
                            style = MaterialTheme.typography.headlineLarge.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace,
                                letterSpacing = 4.sp
                            ),
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.clickable { onCopyCode() }
                        )
                        IconButton(onClick = onRegenerateCode) {
                            Icon(Icons.Default.Refresh, contentDescription = "Regenerate")
                        }
                    }
                    Text(
                        text = "Tap code to copy. Send to Hermes to connect.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                }
            }

            // LLM Section
            SettingsCard(title = "LLM Inference") {
                StatusItem(label = "server", status = llmServerPort, isActive = llmServerRunning)
                StatusItem(label = "model", status = modelStatus, isActive = modelLoaded || modelReady)
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = modelName,
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                
                if (downloadProgress != null) {
                    Spacer(modifier = Modifier.height(4.dp))
                    LinearProgressIndicator(
                        progress = { downloadProgress },
                        modifier = Modifier.fillMaxWidth().height(4.dp),
                        color = MaterialTheme.colorScheme.primary,
                        trackColor = MaterialTheme.colorScheme.surfaceVariant,
                    )
                    Text(
                        text = downloadLabel,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                }
                
                Spacer(modifier = Modifier.height(12.dp))
                
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    val modelActionText = when {
                        downloadProgress != null -> "Pause"
                        !modelReady -> "Download"
                        modelLoaded -> "Reload"
                        else -> "Load"
                    }
                    
                    Button(
                        onClick = onModelAction,
                        modifier = Modifier.weight(1f),
                        shape = MaterialTheme.shapes.medium
                    ) {
                        Text(modelActionText)
                    }
                    
                    Button(
                        onClick = onToggleLlmServer,
                        modifier = Modifier.weight(1f),
                        shape = MaterialTheme.shapes.medium,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (llmServerRunning) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.primaryContainer,
                            contentColor = if (llmServerRunning) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onPrimaryContainer
                        )
                    ) {
                        Text(if (llmServerRunning) "Stop Server" else "Start Server")
                    }
                }
            }

            // Connection Section
            SettingsCard(title = "Connect to Relay") {
                OutlinedTextField(
                    value = serverUrl,
                    onValueChange = onUrlChange,
                    label = { Text("Relay URL") },
                    placeholder = { Text("server-ip:8766") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    shape = MaterialTheme.shapes.medium
                )
                
                Text(
                    text = relayStatus,
                    style = MaterialTheme.typography.bodySmall,
                    color = if (relayConnected) Color(0xFF4CAF50) else MaterialTheme.colorScheme.outline,
                    modifier = Modifier.padding(vertical = 4.dp)
                )
                
                Button(
                    onClick = if (relayConnected) onDisconnect else onConnect,
                    modifier = Modifier.fillMaxWidth(),
                    shape = MaterialTheme.shapes.medium
                ) {
                    Text(if (relayConnected) "DISCONNECT" else "CONNECT")
                }
            }

            Text(
                text = localAddress,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.outline,
                modifier = Modifier.fillMaxWidth(),
                textAlign = androidx.compose.ui.text.style.TextAlign.Center
            )
            
            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}

@Composable
fun SettingsCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp).fillMaxWidth()
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(bottom = 12.dp)
            )
            content()
        }
    }
}

@Composable
fun StatusItem(
    label: String, 
    status: String, 
    isActive: Boolean,
    action: @Composable (() -> Unit)? = null
) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(10.dp)
                .clip(CircleShape)
                .background(if (isActive) Color(0xFF4CAF50) else Color.Gray)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f)
        )
        Text(
            text = status,
            style = MaterialTheme.typography.bodyMedium,
            color = if (isActive) Color(0xFF4CAF50) else MaterialTheme.colorScheme.onSurfaceVariant,
            fontWeight = if (isActive) FontWeight.Bold else FontWeight.Normal
        )
        if (action != null) {
            Spacer(modifier = Modifier.width(8.dp))
            action()
        }
    }
}

@Composable
fun PermissionItem(
    label: String,
    description: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(text = label, style = MaterialTheme.typography.bodyLarge)
            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline
            )
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange
        )
    }
}
