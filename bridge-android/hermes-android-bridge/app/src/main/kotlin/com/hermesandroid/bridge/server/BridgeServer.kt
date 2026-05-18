package com.hermesandroid.bridge.server

import com.hermesandroid.bridge.auth.PairingManager
import io.ktor.http.*
import io.ktor.serialization.gson.*
import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import android.util.Log

object BridgeServer {
    private const val TAG = "BridgeServer"
    private var server: ApplicationEngine? = null

    fun start(port: Int = 8765) {
        if (server != null) return
        Log.i(TAG, "Starting BridgeServer on port $port")
        try {
        server = embeddedServer(Netty, port = port, host = "0.0.0.0") {
            install(ContentNegotiation) {
                gson {
                    setPrettyPrinting()
                    serializeNulls()
                }
            }
            // Auth interceptor — every request must have valid Bearer token
            intercept(ApplicationCallPipeline.Plugins) {
                val path = call.request.path()
                // Allow /ping without auth so the agent can discover the bridge,
                // but it won't return sensitive data without auth
                if (path == "/ping") return@intercept

                val authHeader = call.request.header(HttpHeaders.Authorization)
                if (!PairingManager.validateToken(authHeader)) {
                    call.respond(HttpStatusCode.Unauthorized, mapOf(
                        "error" to "Invalid or missing pairing code",
                        "hint" to "Set ANDROID_BRIDGE_TOKEN to the code shown in the Hermes Bridge app"
                    ))
                    finish()
                }
            }
            configureRouting()
        }.also {
            it.start(wait = false)
            Log.i(TAG, "BridgeServer started successfully on port $port")
        }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start BridgeServer: ${e.message}", e)
        }
    }

    fun stop() {
        server?.stop(1000, 2000)
        server = null
    }

    fun isRunning(): Boolean {
        return server != null
    }
}
