package com.hermesandroid.bridge

import android.app.Application
import android.util.Log
import com.hermesandroid.bridge.auth.PairingManager
import com.hermesandroid.bridge.client.RelayClient
import com.hermesandroid.bridge.llm.LlmService
import com.hermesandroid.bridge.power.WakeLockManager
import com.hermesandroid.bridge.server.BridgeServer

class BridgeApplication : Application() {
    companion object {
        private const val TAG = "BridgeApp"
        lateinit var instance: BridgeApplication
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        Log.e(TAG, "!!! BridgeApplication onCreate START !!!")
        
        PairingManager.init(applicationContext)
        WakeLockManager.init(applicationContext)
        com.hermesandroid.bridge.ui.theme.ThemeManager.init(this)
        
        Log.e(TAG, "Starting BridgeServer (8765)...")
        BridgeServer.start(port = 8765)

        // Start embedded LLM service (persistent foreground service)
        Log.e(TAG, "Starting LlmService (8080)...")
        startLlmServer()

        // Initialize relay client and auto-connect if previously configured
        RelayClient.init(applicationContext)
        RelayClient.autoConnect()
        Log.e(TAG, "!!! BridgeApplication onCreate DONE !!!")
    }

    fun startMainServer() {
        Log.e(TAG, "MANUAL START: MainServer")
        BridgeServer.start(port = 8765)
    }

    fun stopMainServer() {
        Log.e(TAG, "MANUAL STOP: MainServer")
        BridgeServer.stop()
    }

    fun isMainServerRunning(): Boolean {
        return BridgeServer.isRunning()
    }

    fun startLlmServer() {
        try {
            LlmService.start(this)
            Log.e(TAG, "LlmService started successfully")
        } catch (e: Exception) {
            Log.e(TAG, "CRITICAL ERROR: Failed to start LlmService: ${e.message}", e)
        }
    }

    fun stopLlmServer() {
        Log.e(TAG, "MANUAL STOP: LlmService")
        LlmService.stop(this)
    }

    fun isLlmServerRunning(): Boolean {
        return LlmService.isAlive
    }

    override fun onTerminate() {
        super.onTerminate()
        stopLlmServer()
    }
}
