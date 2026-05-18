package com.hermesandroid.bridge.server

import com.hermesandroid.bridge.auth.PairingManager
import com.hermesandroid.bridge.model.ScreenNode
import com.hermesandroid.bridge.executor.ActionExecutor
import com.hermesandroid.bridge.executor.ScreenReader
import com.hermesandroid.bridge.media.ScreenRecorder
import com.hermesandroid.bridge.event.EventStore
import com.hermesandroid.bridge.notification.NotificationStore
import com.hermesandroid.bridge.llm.ModelDownloader
import com.hermesandroid.bridge.service.BridgeAccessibilityService
import com.hermesandroid.bridge.voice.VoiceManager
import com.hermesandroid.bridge.overlay.StatusOverlay
import com.hermesandroid.bridge.client.RelayClient
import com.hermesandroid.bridge.BuildConfig
import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import com.hermesandroid.bridge.chat.ChatEventBus
import com.hermesandroid.bridge.chat.ui.ChatMessageText
import com.hermesandroid.bridge.chat.ui.ChatSide
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

// Data classes for request bodies
data class ChatApiRequest(val role: String, val text: String, val isMarkdown: Boolean = false)
data class OverlayRequest(
    val text: String? = null,
    // Structured dashboard fields (all optional, backward compatible)
    val goal: String? = null,
    val step: Int? = null,
    val maxSteps: Int? = null,
    val status: String? = null,
    val elapsed: Int? = null,
    val model: String? = null,
    val plan: List<String>? = null,
    val planState: List<Boolean>? = null,
    val focusIdx: Int? = null,
    val thinking: String? = null,
    val currentTarget: String? = null,
    val lastActionSuccess: Boolean? = null,
    val lastReflection: String? = null,
    val lastMissionComplete: Boolean? = null,
    val lastMissionReason: String? = null,
    val lastVerify: String? = null,
    val progress: String? = null,
    val scratchpad: List<String>? = null,
    val profile: Map<String, Any>? = null
)
data class DownloadRequest(val url: String, val filename: String)
data class TapRequest(val x: Int? = null, val y: Int? = null, val nodeId: String? = null)
data class TapTextRequest(val text: String, val exact: Boolean = false)
data class TypeRequest(val text: String, val clearFirst: Boolean = false)
data class SwipeRequest(val direction: String, val distance: String = "medium")
data class OpenAppRequest(val packageName: String)
data class PressKeyRequest(val key: String)
data class ScrollRequest(val direction: String, val nodeId: String? = null)
data class WaitRequest(val text: String? = null, val className: String? = null, val timeoutMs: Int = 5000)
data class ClipboardWriteRequest(val text: String)
data class LongPressRequest(val x: Int? = null, val y: Int? = null, val nodeId: String? = null, val duration: Long = 500)
data class DragRequest(val startX: Int, val startY: Int, val endX: Int, val endY: Int, val duration: Long = 500)
data class TapAndTypeRequest(val x: Int, val y: Int, val text: String, val clearFirst: Boolean = false, val editorAction: String? = null)
data class DescribeNodeRequest(val nodeId: String)
data class FindNodesRequest(val text: String? = null, val className: String? = null, val clickable: Boolean? = null, val limit: Int = 20)
data class DiffRequest(val previousHash: String)
data class PinchRequest(val x: Int, val y: Int, val scale: Float = 1.5f, val duration: Long = 300)
data class SmsRequest(val to: String, val body: String)
data class CallRequest(val number: String)
data class MediaRequest(val action: String)
data class IntentRequest(val action: String, val dataUri: String? = null, val extras: Map<String, String>? = null, val packageOverride: String? = null)
data class StreamRequest(val enabled: Boolean)
data class BroadcastRequest(val action: String, val extras: Map<String, String>? = null)
data class RecordRequest(val durationMs: Long = 5000)
data class SpeakRequest(val text: String, val queue: Int = 1)

fun Application.configureRouting() {
    routing {
        post("/voice_start") {
            val ctx = BridgeAccessibilityService.instance
            if (ctx == null) {
                call.respond(HttpStatusCode.ServiceUnavailable, mapOf("success" to false, "message" to "Accessibility Service not running"))
                return@post
            }
            VoiceManager.startListening(ctx, object : VoiceManager.VoiceCallback {
                override fun onPartialResult(text: String) {
                    RelayClient.sendEvent("voice_partial", mapOf("text" to text))
                }
                override fun onFinalResult(text: String) {
                    EventStore.addCustomEvent("voice_final", text)
                    RelayClient.sendEvent("voice_final", mapOf("text" to text))
                }
                override fun onError(error: String) {
                    RelayClient.sendEvent("voice_error", mapOf("message" to error))
                }
            })
            call.respond(mapOf("success" to true, "message" to "Voice recognition started"))
        }

        post("/voice_stop") {
            VoiceManager.stopListening()
            call.respond(mapOf("success" to true, "message" to "Voice recognition stopped"))
        }

        post("/overlay") {
            val req = call.receive<OverlayRequest>()
            // If structured fields present, update dashboard
            if (req.goal != null || req.step != null || req.plan != null || req.thinking != null || req.currentTarget != null) {
                StatusOverlay.updateDashboard(StatusOverlay.DashboardState(
                    goal = req.goal ?: "",
                    step = req.step ?: 0,
                    maxSteps = req.maxSteps ?: 0,
                    status = req.status ?: "",
                    elapsed = req.elapsed ?: 0,
                    model = req.model ?: "",
                    plan = req.plan ?: emptyList(),
                    planState = req.planState ?: emptyList(),
                    focusIdx = req.focusIdx ?: -1,
                    thinking = req.thinking ?: "",
                    currentTarget = req.currentTarget ?: "",
                    lastActionSuccess = req.lastActionSuccess,
                    lastReflection = req.lastReflection ?: "",
                    lastMissionComplete = req.lastMissionComplete,
                    lastMissionReason = req.lastMissionReason ?: "",
                    lastVerify = req.lastVerify ?: "",
                    progress = req.progress ?: "",
                    scratchpad = req.scratchpad ?: emptyList(),
                    profile = req.profile ?: emptyMap()
                ))
            }
            // Only handle plain text when no structured fields (backward compatible)
            if (req.text != null && req.goal == null && req.step == null && req.plan == null) {
                StatusOverlay.updateMessage(req.text)
            }
            call.respond(mapOf("success" to true))
        }

        delete("/overlay") {
            StatusOverlay.reset()
            call.respond(mapOf("success" to true))
        }

        post("/chat") {
            val req = call.receive<ChatApiRequest>()
            val side = if (req.role.equals("user", ignoreCase = true)) ChatSide.USER else ChatSide.AGENT
            val msg = ChatMessageText(
                content = req.text,
                side = side,
                isMarkdown = req.isMarkdown
            )
            ChatEventBus.emitMessage(msg)
            call.respond(mapOf("success" to true))
        }

        get("/models") {
            val dir = java.io.File("/data/local/tmp")
            val models = if (dir.exists()) {
                dir.listFiles()?.filter { it.name.endsWith(".litertlm") }?.map {
                    mapOf("name" to it.name, "path" to it.absolutePath, "size" to it.length())
                } ?: emptyList()
            } else {
                emptyList()
            }
            call.respond(mapOf("models" to models))
        }

        post("/models/download") {
            data class DownloadRequest(val url: String, val filename: String, val token: String? = null)
            val req = call.receive<DownloadRequest>()
            val dest = java.io.File("/data/local/tmp", req.filename)
            
            withContext(Dispatchers.IO) {
                ModelDownloader.download(req.url, dest, req.token) { _, _ -> } 
            }
            call.respond(mapOf("success" to true, "message" to "Download finished for ${req.filename}"))
        }

        get("/ping") {
            val serviceRunning = BridgeAccessibilityService.instance != null
            val authHeader = call.request.header(HttpHeaders.Authorization)
            val authenticated = PairingManager.validateToken(authHeader)
            call.respond(mapOf(
                "status" to "ok",
                "accessibilityService" to serviceRunning,
                "authenticated" to authenticated,
                "version" to BuildConfig.VERSION_NAME
            ))
        }

        get("/screen") {
            val bounds = call.request.queryParameters["bounds"] == "true"
            val tree = withContext(Dispatchers.Main) {
                ScreenReader.readCurrentScreen(bounds)
            }
            call.respond(mapOf("tree" to tree, "count" to countNodes(tree)))
        }

        post("/tap") {
            val req = call.receive<TapRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.tap(req.x, req.y, req.nodeId)
            }
            call.respond(result)
        }

        post("/tap_text") {
            val req = call.receive<TapTextRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.tapText(req.text, req.exact)
            }
            call.respond(result)
        }

        post("/type") {
            val req = call.receive<TypeRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.typeText(req.text, req.clearFirst)
            }
            call.respond(result)
        }

        post("/swipe") {
            val req = call.receive<SwipeRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.swipe(req.direction, req.distance)
            }
            call.respond(result)
        }

        post("/open_app") {
            val req = call.receive<OpenAppRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.openApp(req.packageName)
            }
            call.respond(result)
        }

        post("/press_key") {
            val req = call.receive<PressKeyRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.pressKey(req.key)
            }
            call.respond(result)
        }

        get("/screenshot") {
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.takeScreenshot()
            }
            call.respond(result)
        }

        post("/scroll") {
            val req = call.receive<ScrollRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.scroll(req.direction, req.nodeId)
            }
            call.respond(result)
        }

        post("/wait") {
            val req = call.receive<WaitRequest>()
            val result = ActionExecutor.waitForElement(req.text, req.className, req.timeoutMs)
            call.respond(result)
        }

        post("/tap_and_type") {
            val req = call.receive<TapAndTypeRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.tapAndType(req.x, req.y, req.text, req.clearFirst, req.editorAction)
            }
            call.respond(result)
        }

        get("/apps") {
            val apps = withContext(Dispatchers.Main) {
                ActionExecutor.getInstalledApps()
            }
            call.respond(mapOf("apps" to apps, "count" to apps.size))
        }

        get("/current_app") {
            val result = withContext(Dispatchers.Main) {
                val service = BridgeAccessibilityService.instance
                val root = service?.windows?.firstOrNull()?.root
                val pkg = root?.packageName?.toString() ?: "unknown"
                val cls = root?.className?.toString() ?: "unknown"
                root?.recycle()
                mapOf("package" to pkg, "className" to cls)
            }
            call.respond(result)
        }

        get("/clipboard") {
            val result = ActionExecutor.clipboardRead()
            call.respond(result)
        }

        post("/clipboard") {
            val req = call.receive<ClipboardWriteRequest>()
            val result = ActionExecutor.clipboardWrite(req.text)
            call.respond(result)
        }

        get("/notifications") {
            val limit = call.request.queryParameters["limit"]?.toIntOrNull() ?: 50
            val since = call.request.queryParameters["since"]?.toLongOrNull() ?: 0L
            val entries = if (since > 0) {
                NotificationStore.getSince(since, limit)
            } else {
                NotificationStore.getAll(limit)
            }
            val mapped = entries.map { NotificationStore.toMap(it) }
            val listenerRunning = com.hermesandroid.bridge.service.BridgeNotificationListener.instance != null
            call.respond(mapOf(
                "notifications" to mapped,
                "count" to mapped.size,
                "listenerActive" to listenerRunning
            ))
        }

        post("/long_press") {
            val req = call.receive<LongPressRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.longPress(req.x, req.y, req.nodeId, req.duration)
            }
            call.respond(result)
        }

        post("/drag") {
            val req = call.receive<DragRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.drag(req.startX, req.startY, req.endX, req.endY, req.duration)
            }
            call.respond(result)
        }

        post("/describe_node") {
            val req = call.receive<DescribeNodeRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.describeNode(req.nodeId)
            }
            call.respond(result)
        }

        post("/find_nodes") {
            val req = call.receive<FindNodesRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.findNodes(req.text, req.className, req.clickable, req.limit)
            }
            call.respond(result)
        }

        post("/diff_screen") {
            val req = call.receive<DiffRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.diffScreen(req.previousHash)
            }
            call.respond(result)
        }

        post("/pinch") {
            val req = call.receive<PinchRequest>()
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.pinch(req.x, req.y, req.scale, req.duration)
            }
            call.respond(result)
        }

        get("/screen_hash") {
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.screenHash()
            }
            call.respond(result)
        }

        get("/location") {
            val result = ActionExecutor.location()
            call.respond(result)
        }

        post("/send_sms") {
            val req = call.receive<SmsRequest>()
            val result = ActionExecutor.sendSms(req.to, req.body)
            call.respond(result)
        }

        post("/call") {
            val req = call.receive<CallRequest>()
            val result = ActionExecutor.makeCall(req.number)
            call.respond(result)
        }

        post("/media") {
            val req = call.receive<MediaRequest>()
            val result = ActionExecutor.mediaControl(req.action)
            call.respond(result)
        }

        get("/contacts") {
            val query = call.request.queryParameters["query"] ?: ""
            val limit = call.request.queryParameters["limit"]?.toIntOrNull() ?: 20
            val result = withContext(Dispatchers.IO) {
                ActionExecutor.searchContacts(query, limit)
            }
            call.respond(result)
        }

        post("/intent") {
            val req = call.receive<IntentRequest>()
            val result = ActionExecutor.sendIntent(req.action, req.dataUri, req.extras, req.packageOverride)
            call.respond(result)
        }

        get("/events") {
            val limit = call.request.queryParameters["limit"]?.toIntOrNull() ?: 50
            val since = call.request.queryParameters["since"]?.toLongOrNull() ?: 0L
            val entries = if (since > 0) {
                EventStore.getSince(since, limit)
            } else {
                EventStore.getAll(limit)
            }
            val mapped = entries.map { EventStore.toMap(it) }
            call.respond(mapOf(
                "events" to mapped,
                "count" to mapped.size,
                "streaming" to EventStore.streamingEnabled
            ))
        }

        post("/events/stream") {
            val req = call.receive<StreamRequest>()
            EventStore.setStreaming(req.enabled)
            call.respond(mapOf("success" to true, "streaming" to req.enabled))
        }

        post("/broadcast") {
            val req = call.receive<BroadcastRequest>()
            val result = ActionExecutor.sendBroadcast(req.action, req.extras)
            call.respond(result)
        }

        post("/screen_record") {
            val req = call.receive<RecordRequest>()
            val result = ScreenRecorder.record(req.durationMs)
            call.respond(result)
        }

        get("/widgets") {
            val result = withContext(Dispatchers.Main) {
                ActionExecutor.readWidgets()
            }
            call.respond(result)
        }

        post("/speak") {
            val req = call.receive<SpeakRequest>()
            val result = ActionExecutor.speak(req.text, req.queue)
            call.respond(result)
        }

        post("/stop_speaking") {
            val result = ActionExecutor.stopSpeaking()
            call.respond(result)
        }
    }
}

private fun countNodes(nodes: List<Any>): Int {
    var count = 0
    for (node in nodes) {
        count++
        if (node is ScreenNode) {
            count += countNodeChildren(node)
        }
    }
    return count
}

private fun countNodeChildren(node: ScreenNode): Int {
    var count = node.children.size
    for (child in node.children) {
        count += countNodeChildren(child)
    }
    return count
}
