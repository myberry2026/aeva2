package com.hermesandroid.bridge

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import com.hermesandroid.bridge.auth.PairingManager
import com.hermesandroid.bridge.client.RelayClient
import com.hermesandroid.bridge.llm.LlmInferenceManager
import com.hermesandroid.bridge.llm.ModelDownloader
import com.hermesandroid.bridge.media.ScreenRecorder
import com.hermesandroid.bridge.overlay.StatusOverlay
import com.hermesandroid.bridge.service.BridgeAccessibilityService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.File
import java.net.NetworkInterface
import java.util.concurrent.TimeUnit

class SettingsActivity : Activity() {

    companion object {
        private const val TAG = "BridgeSettingsActivity"
        private const val REQUEST_CODE_SCREEN_RECORD = 1001
    }

    private lateinit var tvA11yStatus: TextView
    private lateinit var tvServerStatus: TextView
    private lateinit var tvRelayAddr: TextView
    private lateinit var tvAuthCode: TextView
    private lateinit var indicatorA11y: View
    private lateinit var indicatorServer: View
    private lateinit var indicatorRelay: View
    private lateinit var indicatorAuth: View
    private lateinit var indicatorAgent: View
    private lateinit var tvAgentStatus: TextView
    private lateinit var btnToggleMainServer: Button
    private lateinit var btnBack: ImageView

    // LLM components
    private lateinit var tvLlmServerStatus: TextView
    private lateinit var tvModelStatus: TextView
    private lateinit var indicatorLlmServer: View
    private lateinit var indicatorModel: View
    private lateinit var btnReloadModel: Button
    private lateinit var btnToggleLlmServer: Button
    
    private lateinit var tvModelName: TextView
    private lateinit var pbDownload: ProgressBar
    private lateinit var tvDownloadProgress: TextView

    private lateinit var switchAccessibility: Switch
    private lateinit var switchOverlay: Switch
    private lateinit var switchScreenRecord: Switch
    private lateinit var tvPairingCode: TextView
    private lateinit var btnRegenerate: Button
    private lateinit var etServerUrl: EditText
    private lateinit var tvRelayStatus: TextView
    private lateinit var btnConnect: Button
    private lateinit var btnDisconnect: Button
    private lateinit var tvAddress: TextView

    private val handler = Handler(Looper.getMainLooper())
    private val statusUpdateRunnable = object : Runnable {
        override fun run() {
            updateStatus()
            handler.postDelayed(this, 2000)
        }
    }

    private var downloadJob: Job? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        val isDark = com.hermesandroid.bridge.ui.theme.ThemeManager.isDarkMode.value
        setTheme(if (isDark) R.style.Theme_HermesBridge_Night else R.style.Theme_HermesBridge_Day)
        super.onCreate(savedInstanceState)
        Log.e(TAG, "onCreate: Initializing SettingsActivity")
        setContentView(R.layout.activity_main)

        // Bind views
        tvA11yStatus = findViewById(R.id.tvA11yStatus)
        tvServerStatus = findViewById(R.id.tvServerStatus)
        tvRelayAddr = findViewById(R.id.tvRelayAddr)
        tvAuthCode = findViewById(R.id.tvAuthCode)
        indicatorA11y = findViewById(R.id.indicatorA11y)
        indicatorServer = findViewById(R.id.indicatorServer)
        indicatorRelay = findViewById(R.id.indicatorRelay)
        indicatorAuth = findViewById(R.id.indicatorAuth)
        indicatorAgent = findViewById(R.id.indicatorAgent)
        tvAgentStatus = findViewById(R.id.tvAgentStatus)
        btnToggleMainServer = findViewById(R.id.btnToggleMainServer)
        
        btnBack = findViewById(R.id.btnBack)
        btnBack.setOnClickListener { finish() }

        tvLlmServerStatus = findViewById(R.id.tvLlmServerStatus)
        tvModelStatus = findViewById(R.id.tvModelStatus)
        indicatorLlmServer = findViewById(R.id.indicatorLlmServer)
        indicatorModel = findViewById(R.id.indicatorModel)
        btnReloadModel = findViewById(R.id.btnReloadModel)
        btnToggleLlmServer = findViewById(R.id.btnToggleLlmServer)
        
        tvModelName = findViewById(R.id.tvModelName)
        pbDownload = findViewById(R.id.pbDownload)
        tvDownloadProgress = findViewById(R.id.tvDownloadProgress)

        switchAccessibility = findViewById(R.id.switchAccessibility)
        switchOverlay = findViewById(R.id.switchOverlay)
        switchScreenRecord = findViewById(R.id.switchScreenRecord)
        tvPairingCode = findViewById(R.id.tvPairingCode)
        btnRegenerate = findViewById(R.id.btnRegenerate)
        etServerUrl = findViewById(R.id.etServerUrl)
        tvRelayStatus = findViewById(R.id.tvRelayStatus)
        btnConnect = findViewById(R.id.btnConnect)
        btnDisconnect = findViewById(R.id.btnDisconnect)
        tvAddress = findViewById(R.id.tvAddress)

        setupPairingCode()
        setupPermissions()
        setupRelayConnection()
        setupServerControls()

        updateConnectionInfo()
        updateStatus()

        handler.post(statusUpdateRunnable)
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacks(statusUpdateRunnable)
        downloadJob?.cancel()
    }

    override fun onResume() {
        super.onResume()
        updateStatus()
        updatePermissionSwitches()
    }

    private fun setupServerControls() {
        btnToggleMainServer.setOnClickListener {
            val app = BridgeApplication.instance
            if (app.isMainServerRunning()) app.stopMainServer() else app.startMainServer()
            updateStatus()
        }

        btnToggleLlmServer.setOnClickListener {
            val app = BridgeApplication.instance
            if (app.isLlmServerRunning()) app.stopLlmServer() else app.startLlmServer()
            updateStatus()
        }

        btnReloadModel.setOnClickListener {
            if (downloadJob != null && downloadJob?.isActive == true) {
                // Pause clicked
                downloadJob?.cancel()
                downloadJob = null
                btnReloadModel.text = "Resume"
                Toast.makeText(this, "Download Paused", Toast.LENGTH_SHORT).show()
                updateStatus()
                return@setOnClickListener
            }

            val modelFile = findDefaultModel()
            if (modelFile == null) {
                // Clean up any stale job before starting
                downloadJob?.cancel()
                downloadJob = null
                startModelDownload()
            } else {
                performModelReload(modelFile)
            }
        }
    }

    private fun startModelDownload() {
        downloadJob = CoroutineScope(Dispatchers.Main).launch {
            btnReloadModel.text = "Pause"
            pbDownload.visibility = View.VISIBLE
            tvDownloadProgress.visibility = View.VISIBLE
            
            val destDir = File(getExternalFilesDir(null), "models")
            if (!destDir.exists()) destDir.mkdirs()
            val targetFile = File(destDir, ModelDownloader.DEFAULT_MODEL_FILE)
            
            val url = ModelDownloader.getDownloadUrl(
                ModelDownloader.DEFAULT_MODEL_ID,
                ModelDownloader.DEFAULT_COMMIT_HASH,
                ModelDownloader.DEFAULT_MODEL_FILE
            )
            
            val success = ModelDownloader.download(url, targetFile) { received, total ->
                CoroutineScope(Dispatchers.Main).launch {
                    val progress = if (total > 0) (received * 100 / total).toInt() else 0
                    pbDownload.progress = progress
                    tvDownloadProgress.text = "$progress% (${formatSize(received)}/${formatSize(total)})"
                }
            }
            
            if (success) {
                Toast.makeText(this@SettingsActivity, "Download Complete!", Toast.LENGTH_SHORT).show()
                performModelReload(targetFile.absolutePath)
            }
            
            pbDownload.visibility = View.GONE
            tvDownloadProgress.visibility = View.GONE
            downloadJob = null
            updateStatus()
        }
    }

    private fun performModelReload(path: String) {
        CoroutineScope(Dispatchers.Main).launch {
            btnReloadModel.isEnabled = false
            btnReloadModel.text = "Loading..."
            try {
                LlmInferenceManager.loadModel(path)
                Toast.makeText(this@SettingsActivity, "Model Loaded", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Toast.makeText(this@SettingsActivity, "Load Error: ${e.message}", Toast.LENGTH_LONG).show()
            }
            btnReloadModel.isEnabled = true
            updateStatus()
        }
    }

    private fun formatSize(bytes: Long): String {
        if (bytes <= 0) return "0B"
        val units = arrayOf("B", "KB", "MB", "GB")
        val digitGroups = (Math.log10(bytes.toDouble()) / Math.log10(1024.0)).toInt()
        return String.format("%.1f%s", bytes / Math.pow(1024.0, digitGroups.toDouble()), units[digitGroups])
    }

    private fun findDefaultModel(): String? {
        val searchPaths = listOf(
            File(getExternalFilesDir(null), "models").absolutePath,
            "/sdcard/Download",
            "/data/local/tmp",
            "/sdcard/Android/data/com.hermesandroid.bridge/files/models"
        )
        for (dir in searchPaths) {
            val f = File(dir)
            if (f.isDirectory) {
                val litertlm = f.listFiles()?.firstOrNull { it.name.endsWith(".litertlm") }
                if (litertlm != null) return litertlm.absolutePath
            }
        }
        return null
    }

    private fun setupPairingCode() {
        tvPairingCode.text = PairingManager.getCode()
        btnRegenerate.setOnClickListener {
            PairingManager.regenerateCode()
            tvPairingCode.text = PairingManager.getCode()
        }
        tvPairingCode.setOnClickListener {
            val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(ClipData.newPlainText("Aeva pairing code", PairingManager.getCode()))
            Toast.makeText(this, "Copied", Toast.LENGTH_SHORT).show()
        }
    }

    private fun setupPermissions() {
        switchAccessibility.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked && BridgeAccessibilityService.instance == null) {
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            }
        }
        switchOverlay.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked) {
                if (!Settings.canDrawOverlays(this)) {
                    startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
                } else StatusOverlay.show(this)
            } else StatusOverlay.hide(this)
        }
        switchScreenRecord.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked && !ScreenRecorder.hasPermission()) {
                val service = BridgeAccessibilityService.instance
                if (service != null) {
                    service.startForeground()
                    val mpm = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
                    startActivityForResult(mpm.createScreenCaptureIntent(), REQUEST_CODE_SCREEN_RECORD)
                }
            }
        }
    }

    private fun updatePermissionSwitches() {
        switchAccessibility.setOnCheckedChangeListener(null)
        switchOverlay.setOnCheckedChangeListener(null)
        switchScreenRecord.setOnCheckedChangeListener(null)

        switchAccessibility.isChecked = BridgeAccessibilityService.instance != null
        
        val hasOverlay = Settings.canDrawOverlays(this)
        switchOverlay.isChecked = hasOverlay
        if (hasOverlay) {
            StatusOverlay.show(this)
        } else {
            StatusOverlay.hide(this)
        }
        
        switchScreenRecord.isChecked = ScreenRecorder.hasPermission()
        
        setupPermissions()
    }

    private fun setupRelayConnection() {
        etServerUrl.setText(RelayClient.serverUrl ?: "")
        RelayClient.onStatusChanged = { connected, message ->
            tvRelayStatus.text = message
            tvRelayStatus.setTextColor(if (connected) 0xFF4CAF50.toInt() else 0xFF888888.toInt())
            updateStatus()
        }
        btnConnect.setOnClickListener {
            val url = etServerUrl.text.toString().trim()
            if (url.isBlank()) RelayClient.disconnect() else RelayClient.connect(url, PairingManager.getCode())
        }
        btnDisconnect.setOnClickListener { RelayClient.disconnect() }
    }

    private fun updateConnectionInfo() {
        tvAddress.text = "http://${getLocalIpAddress()}:8765 (USB/LAN)"
    }

    private fun updateStatus() {
        try {
            val app = BridgeApplication.instance
            
            val serviceRunning = BridgeAccessibilityService.instance != null
            tvA11yStatus.text = if (serviceRunning) "active" else "inactive"
            indicatorA11y.setBackgroundResource(if (serviceRunning) R.drawable.bg_status_dot_green else R.drawable.bg_status_dot_grey)

            val mainRunning = app.isMainServerRunning()
            tvServerStatus.text = if (mainRunning) "8765" else "stopped"
            indicatorServer.setBackgroundResource(if (mainRunning) R.drawable.bg_status_dot_green else R.drawable.bg_status_dot_grey)
            btnToggleMainServer.text = if (mainRunning) "Stop Server" else "Start Server"

            val llmRunning = app.isLlmServerRunning()
            tvLlmServerStatus.text = if (llmRunning) "8080" else "stopped"
            indicatorLlmServer.setBackgroundResource(if (llmRunning) R.drawable.bg_status_dot_green else R.drawable.bg_status_dot_grey)
            btnToggleLlmServer.text = if (llmRunning) "Stop Server" else "Start Server"

            val localModel = findDefaultModel()
            val modelLoaded = LlmInferenceManager.isLoaded
            
            tvModelStatus.text = if (modelLoaded) "Loaded" else if (localModel != null) "Ready" else "Missing"
            indicatorModel.setBackgroundResource(if (modelLoaded) R.drawable.bg_status_dot_green else if (localModel != null) R.drawable.bg_status_dot_blue else R.drawable.bg_status_dot_grey)
            
            tvModelName.text = if (localModel != null) File(localModel).name else ModelDownloader.DEFAULT_MODEL_NAME
            
            if (downloadJob != null && downloadJob?.isActive == true) {
                btnReloadModel.text = "Pause"
            } else {
                btnReloadModel.text = if (localModel == null) {
                    val tmpFile = File(getExternalFilesDir(null), "models/${ModelDownloader.DEFAULT_MODEL_FILE}.tmp")
                    if (tmpFile.exists()) "Resume" else "Download"
                } else if (modelLoaded) "Reload" else "Load"
            }

            tvAuthCode.text = PairingManager.getCode()

            updateAgentStatus()
        } catch (e: Exception) {}
    }

    private val agentClient = OkHttpClient.Builder()
        .connectTimeout(1, TimeUnit.SECONDS)
        .readTimeout(1, TimeUnit.SECONDS)
        .build()

    private fun updateAgentStatus() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val req = Request.Builder()
                    .url("http://127.0.0.1:8767/health")
                    .build()
                val resp = agentClient.newCall(req).execute()
                val ok = resp.isSuccessful
                CoroutineScope(Dispatchers.Main).launch {
                    indicatorAgent.setBackgroundResource(
                        if (ok) R.drawable.bg_status_dot_green else R.drawable.bg_status_dot_grey
                    )
                    tvAgentStatus.text = if (ok) "8767" else "error"
                    tvAgentStatus.setTextColor(if (ok) 0xFF10B981.toInt() else 0xFFA1A1AA.toInt())
                }
            } catch (_: Exception) {
                CoroutineScope(Dispatchers.Main).launch {
                    indicatorAgent.setBackgroundResource(R.drawable.bg_status_dot_grey)
                    tvAgentStatus.text = "offline"
                    tvAgentStatus.setTextColor(0xFFA1A1AA.toInt())
                }
            }
        }
    }

    private fun getLocalIpAddress(): String {
        return NetworkInterface.getNetworkInterfaces()?.toList()
            ?.flatMap { it.inetAddresses.toList() }
            ?.firstOrNull { !it.isLoopbackAddress && it.hostAddress?.contains(':') == false }
            ?.hostAddress ?: "localhost"
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQUEST_CODE_SCREEN_RECORD && resultCode == RESULT_OK && data != null) {
            val mpm = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            ScreenRecorder.setProjection(mpm.getMediaProjection(resultCode, data))
            updatePermissionSwitches()
        }
    }
}
