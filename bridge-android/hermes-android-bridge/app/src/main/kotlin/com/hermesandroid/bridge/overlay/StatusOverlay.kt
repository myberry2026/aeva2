package com.hermesandroid.bridge.overlay

import android.content.Context
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.hermesandroid.bridge.voice.VoiceManager
import com.hermesandroid.bridge.client.RelayClient
import com.hermesandroid.bridge.service.BridgeAccessibilityService
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import com.hermesandroid.bridge.executor.ActionExecutor
import com.hermesandroid.bridge.R

object StatusOverlay {
    private var overlayView: View? = null
    private var params: WindowManager.LayoutParams? = null

    // Section views
    private var headerText: TextView? = null
    private var statusLine: TextView? = null
    private var planText: TextView? = null
    private var thinkingText: TextView? = null
    private var actionText: TextView? = null
    private var scratchpadText: TextView? = null
    private var profileText: TextView? = null
    private var messageText: TextView? = null
    private var messageScrollView: ScrollView? = null
    private var indicatorView: View? = null

    // State
    private var isListening = false
    private val messageHistory = StringBuilder()

    // Dashboard state
    data class DashboardState(
        val goal: String = "",
        val step: Int = 0,
        val maxSteps: Int = 0,
        val status: String = "",
        val elapsed: Int = 0,
        val model: String = "",
        val plan: List<String> = emptyList(),
        val planState: List<Boolean> = emptyList(),
        val focusIdx: Int = -1,
        val thinking: String = "",
        val currentTarget: String = "",
        val lastActionSuccess: Boolean? = null,
        val lastReflection: String = "",
        val lastMissionComplete: Boolean? = null,
        val lastMissionReason: String = "",
        val lastVerify: String = "",
        val progress: String = "",
        val scratchpad: List<String> = emptyList(),
        val profile: Map<String, Any> = emptyMap()
    )

    private var dashboardState = DashboardState()

    fun show(context: Context) {
        if (overlayView != null) return

        val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val density = context.resources.displayMetrics.density

        val container = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 16, 24, 16)
            background = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = 32f
                setColor(Color.parseColor("#E6000000"))
                setStroke(2, Color.parseColor("#33FFFFFF"))
            }
        }

        // ── Header: goal + indicator ──
        val headerRow = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val indicator = View(context).apply {
            val size = (12 * density).toInt()
            layoutParams = LinearLayout.LayoutParams(size, size).apply { marginEnd = (8 * density).toInt() }
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(Color.RED)
            }
        }
        indicatorView = indicator
        headerText = TextView(context).apply {
            textSize = 13f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            maxLines = 1
            text = "Aeva"
        }
        headerRow.addView(indicator)
        headerRow.addView(headerText, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))

        // ── Status line: step / elapsed / model ──
        statusLine = TextView(context).apply {
            textSize = 11f
            setTextColor(Color.parseColor("#AAAAAA"))
            typeface = Typeface.MONOSPACE
            setPadding(0, (4 * density).toInt(), 0, (8 * density).toInt())
            text = ""
        }

        // ── Plan checklist ──
        planText = TextView(context).apply {
            textSize = 11f
            setTextColor(Color.parseColor("#CCCCCC"))
            typeface = Typeface.MONOSPACE
            maxLines = 8
            setPadding(0, 0, 0, (6 * density).toInt())
            text = ""
            visibility = View.GONE
        }

        // ── Thinking ──
        thinkingText = TextView(context).apply {
            textSize = 11f
            setTextColor(Color.parseColor("#88CCFF"))
            typeface = Typeface.MONOSPACE
            maxLines = 8
            setPadding(0, 0, 0, (6 * density).toInt())
            text = ""
            visibility = View.GONE
        }

        // ── Action result ──
        actionText = TextView(context).apply {
            textSize = 11f
            setTextColor(Color.parseColor("#AAAAAA"))
            typeface = Typeface.MONOSPACE
            maxLines = 2
            setPadding(0, 0, 0, (6 * density).toInt())
            text = ""
            visibility = View.GONE
        }

        // ── Scratchpad ──
        scratchpadText = TextView(context).apply {
            textSize = 10f
            setTextColor(Color.parseColor("#88CCFF"))
            typeface = Typeface.MONOSPACE
            maxLines = 6
            setPadding(0, 0, 0, (6 * density).toInt())
            text = ""
            visibility = View.GONE
        }

        // ── Profile ──
        profileText = TextView(context).apply {
            textSize = 10f
            setTextColor(Color.parseColor("#888888"))
            typeface = Typeface.MONOSPACE
            maxLines = 1
            setPadding(0, 0, 0, (4 * density).toInt())
            text = ""
            visibility = View.GONE
        }

        // ── Divider ──
        val dividerContainer = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, (8 * density).toInt(), 0, (8 * density).toInt())
        }
        val divider = View(context).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, (2 * density).toInt()
            )
            setBackgroundColor(Color.parseColor("#66FFFFFF"))
        }
        dividerContainer.addView(divider)

        // ── Messages (voice + agent) ──
        val msgScrollView = ScrollView(context).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
            )
            isVerticalScrollBarEnabled = false
        }
        messageScrollView = msgScrollView
        messageText = TextView(context).apply {
            textSize = 11f
            setTextColor(Color.WHITE)
            typeface = Typeface.MONOSPACE
            text = "READY..."
        }
        msgScrollView.addView(messageText)

        // ── Assemble ──
        container.addView(headerRow)
        container.addView(statusLine)
        container.addView(planText)
        container.addView(thinkingText)
        container.addView(actionText)
        container.addView(scratchpadText)
        container.addView(profileText)
        container.addView(dividerContainer)
        container.addView(msgScrollView)

        val lp = WindowManager.LayoutParams(
            (280 * density).toInt(),
            (380 * density).toInt(),
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.END
            x = (16 * density).toInt()
            y = (100 * density).toInt()
        }
        params = lp

        // DRAG on header row and container (not on ScrollView, so scrolling works)
        val dragTouchListener = object : View.OnTouchListener {
            private var initialX: Int = 0
            private var initialY: Int = 0
            private var initialTouchX: Float = 0f
            private var initialTouchY: Float = 0f
            private var isDragging = false

            override fun onTouch(v: View, event: MotionEvent): Boolean {
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        initialX = lp.x
                        initialY = lp.y
                        initialTouchX = event.rawX
                        initialTouchY = event.rawY
                        isDragging = false
                        return true
                    }
                    MotionEvent.ACTION_MOVE -> {
                        val dx = (event.rawX - initialTouchX).toInt()
                        val dy = (event.rawY - initialTouchY).toInt()
                        if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
                            isDragging = true
                            lp.x = initialX - dx
                            lp.y = initialY + dy
                            wm.updateViewLayout(container, lp)
                        }
                        return true
                    }
                    MotionEvent.ACTION_UP -> {
                        if (!isDragging) v.performClick()
                        return true
                    }
                }
                return false
            }
        }
        
        headerRow.setOnTouchListener(dragTouchListener)
        container.setOnTouchListener(dragTouchListener)

        // CLICK on header to toggle voice
        headerRow.setOnClickListener {
            if (isListening) stopVoice() else startVoice(context)
        }

        wm.addView(container, lp)
        overlayView = container
    }

    // ── Voice ──

    private fun startVoice(context: Context) {
        val ctx = BridgeAccessibilityService.instance ?: context
        if (isListening) return

        isListening = true
        updateIndicator(true)
        appendMessage("\n> ")

        VoiceManager.startListening(ctx, object : VoiceManager.VoiceCallback {
            override fun onPartialResult(text: String) {
                updateLiveMessage(text)
                RelayClient.sendEvent("voice_partial", mapOf("text" to text))
            }
            override fun onFinalResult(text: String) {
                commitMessage(text)
                com.hermesandroid.bridge.event.EventStore.addCustomEvent("voice_final", text)
                RelayClient.sendEvent("voice_final", mapOf("text" to text))

                com.hermesandroid.bridge.chat.ChatEventBus.emitMessage(
                    com.hermesandroid.bridge.chat.ui.ChatMessageText(
                        content = text,
                        side = com.hermesandroid.bridge.chat.ui.ChatSide.USER,
                        isMarkdown = false
                    )
                )

                if (isListening) {
                    android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                        if (isListening) VoiceManager.startListening(ctx, this)
                    }, 100)
                }
            }
            override fun onError(error: String) {
                if (isListening) {
                    VoiceManager.startListening(ctx, this)
                } else {
                    stopVoice()
                }
            }
        })
    }

    private fun stopVoice() {
        isListening = false
        VoiceManager.stopListening()
        updateIndicator(false)
    }

    private fun updateIndicator(listening: Boolean) {
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            indicatorView?.let { (it.background as GradientDrawable).apply {
                setColor(if (listening) Color.parseColor("#444444") else Color.RED)
                setStroke(if (listening) 4 else 2, if (listening) Color.WHITE else Color.parseColor("#888888"))
            }}
        }
    }

    // ── Dashboard state update (structured) ──

    private var lastRenderedState: DashboardState? = null

    fun updateDashboard(state: DashboardState) {
        // Skip if state hasn't changed (dirty check)
        if (state == lastRenderedState) return
        
        val previousMissionComplete = dashboardState.lastMissionComplete
        val previousStatus = dashboardState.status
        dashboardState = state
        
        // Edge trigger for mission completion
        if (state.lastMissionComplete == true && previousMissionComplete != true) {
            triggerFeedback(true)
            val resultText = buildString {
                append("✅ **Task Completed**")
                if (state.scratchpad.isNotEmpty()) {
                    append("\n\n**Findings:**\n")
                    state.scratchpad.forEach { append("- $it\n") }
                }
            }
            com.hermesandroid.bridge.chat.ChatEventBus.emitMessage(
                com.hermesandroid.bridge.chat.ui.ChatMessageText(
                    content = resultText,
                    side = com.hermesandroid.bridge.chat.ui.ChatSide.AGENT,
                    isMarkdown = true
                )
            )
        } else if ((state.status.contains("EXHAUSTED") || state.status.contains("FAIL")) && 
                   !(previousStatus.contains("EXHAUSTED") || previousStatus.contains("FAIL"))) {
            triggerFeedback(false)
            val resultText = buildString {
                append("❌ **Task Failed / Stopped**")
                if (state.scratchpad.isNotEmpty()) {
                    append("\n\n**Partial Findings:**\n")
                    state.scratchpad.forEach { append("- $it\n") }
                }
            }
            com.hermesandroid.bridge.chat.ChatEventBus.emitMessage(
                com.hermesandroid.bridge.chat.ui.ChatMessageText(
                    content = resultText,
                    side = com.hermesandroid.bridge.chat.ui.ChatSide.AGENT,
                    isMarkdown = true
                )
            )
        }

        android.os.Handler(android.os.Looper.getMainLooper()).post {
            renderDashboard()
        }
    }

    private fun triggerFeedback(success: Boolean) {
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            val ctx = BridgeAccessibilityService.instance ?: return@post

            // Agent run finished — let the user interact with the overlay again.
            setTouchable(true)

            // 1. Audio Feedback
            if (success) {
                ActionExecutor.speak(ctx.getString(R.string.task_finished_tts))
            } else {
                ActionExecutor.speak(ctx.getString(R.string.task_failed_tts))
            }
        }
    }

    private fun renderDashboard() {
        val s = dashboardState
        lastRenderedState = s

        // Header
        headerText?.text = if (s.goal.isNotEmpty()) s.goal else "Aeva"

        // Status line
        val parts = mutableListOf<String>()
        if (s.step > 0) parts.add("Step ${s.step}/${s.maxSteps}")
        if (s.status.isNotEmpty()) parts.add(s.status)
        if (s.elapsed > 0) parts.add("${s.elapsed}s")
        if (s.model.isNotEmpty()) parts.add(s.model)
        statusLine?.text = if (parts.isNotEmpty()) parts.joinToString("  |  ") else ""

        // Status color
        val statusColor = when {
            s.status.contains("SUCCESS") -> Color.parseColor("#44FF44")
            s.status.contains("FAIL") || s.status.contains("EXHAUSTED") -> Color.parseColor("#FF4444")
            s.status.contains("WAITING") -> Color.parseColor("#FFAA00")
            s.status.isNotEmpty() -> Color.parseColor("#44CCFF")
            else -> Color.parseColor("#AAAAAA")
        }
        statusLine?.setTextColor(statusColor)

        // Plan
        if (s.plan.isNotEmpty()) {
            val sb = StringBuilder()
            s.plan.forEachIndexed { i, task ->
                val done = s.planState.getOrNull(i) == true
                val focused = i == s.focusIdx
                val icon = when {
                    done -> "✅"
                    focused -> "▶"
                    else -> "⏳"
                }
                sb.appendLine("$icon $task")
            }
            val doneCount = s.planState.count { it }
            sb.append("[${doneCount}/${s.plan.size} done]")
            planText?.text = sb.toString()
            planText?.visibility = View.VISIBLE
        } else {
            planText?.visibility = View.GONE
        }

        // Thinking
        if (s.thinking.isNotEmpty()) {
            thinkingText?.text = "🔥 ${s.thinking}"
            thinkingText?.visibility = View.VISIBLE
        } else {
            thinkingText?.visibility = View.GONE
        }

        // Action + Mission
        val actionParts = mutableListOf<String>()
        if (s.currentTarget.isNotEmpty()) actionParts.add("⚡ ${s.currentTarget}")
        if (s.lastActionSuccess != null) {
            actionParts.add(if (s.lastActionSuccess) "✓ Action: ${s.lastReflection.take(80)}" else "✗ Action: ${s.lastReflection.take(80)}")
        }
        if (s.lastMissionComplete != null) {
            val missionIcon = if (s.lastMissionComplete) "🏁" else "🏁"
            val missionText = if (s.lastMissionReason.isNotEmpty()) s.lastMissionReason.take(80) else ""
            actionParts.add("$missionIcon Mission: ${if (s.lastMissionComplete) "done" else "not done"} $missionText")
        }
        if (s.lastVerify.isNotEmpty()) actionParts.add("📋 ${s.lastVerify.take(100)}")
        if (s.progress.isNotEmpty()) actionParts.add("📈 ${s.progress}")
        if (actionParts.isNotEmpty()) {
            actionText?.text = actionParts.joinToString("\n")
            actionText?.visibility = View.VISIBLE
        } else {
            actionText?.visibility = View.GONE
        }

        // Scratchpad
        if (s.scratchpad.isNotEmpty()) {
            val sb = StringBuilder()
            for (note in s.scratchpad.takeLast(6)) {
                sb.appendLine("• ${note.take(80)}")
            }
            scratchpadText?.text = sb.toString().trimEnd()
            scratchpadText?.visibility = View.VISIBLE
        } else {
            scratchpadText?.visibility = View.GONE
        }

        // Profile
        if (s.profile.isNotEmpty()) {
            val wall = (s.profile["wall"] as? Number)?.toInt() ?: 0
            val llm = (s.profile["llm"] as? Number)?.toDouble() ?: 0.0
            val inTok = (s.profile["in_tok"] as? Number)?.toInt() ?: 0
            val outTok = (s.profile["out_tok"] as? Number)?.toInt() ?: 0
            profileText?.text = "⏱ ${wall}s | LLM ${llm}s | in=$inTok out=$outTok"
            profileText?.visibility = View.VISIBLE
        } else {
            profileText?.visibility = View.GONE
        }
    }

    // ── Message text updates (backward compatible) ──

    private fun updateLiveMessage(text: String) {
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            messageText?.text = messageHistory.toString() + text
            scrollToBottom()
        }
    }

    private fun commitMessage(text: String) {
        messageHistory.append(text).append(" ")
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            messageText?.text = messageHistory.toString()
            scrollToBottom()
        }
    }

    private fun appendMessage(text: String) {
        messageHistory.append(text)
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            messageText?.text = messageHistory.toString()
            scrollToBottom()
        }
    }

    private fun scrollToBottom() {
        messageScrollView?.post { messageScrollView?.fullScroll(View.FOCUS_DOWN) }
    }

    // ── Public API ──

    fun reset() {
        dashboardState = DashboardState()
        lastRenderedState = null
        messageHistory.setLength(0)
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            renderDashboard()
            messageText?.text = ""
        }
    }

    fun updateMessage(text: String?) {
        if (text == null) {
            messageHistory.setLength(0)
            messageHistory.append("Cleared\n---")
        } else {
            appendMessage("\nAgent: $text")
        }
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            messageText?.text = messageHistory.toString()
            scrollToBottom()
        }
    }

    fun hide(context: Context) {
        val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        overlayView?.let { try { wm.removeView(it) } catch (_: Exception) {} }
        overlayView = null
        headerText = null
        statusLine = null
        planText = null
        thinkingText = null
        actionText = null
        scratchpadText = null
        profileText = null
        messageText = null
        messageScrollView = null
        indicatorView = null
    }

    fun setVisible(visible: Boolean) {
        val view = overlayView ?: return
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            view.visibility = if (visible) View.VISIBLE else View.GONE
        }
    }

    fun setTouchable(touchable: Boolean) {
        val view = overlayView ?: return
        val lp = params ?: return
        val wm = view.context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        
        if (touchable) {
            lp.flags = lp.flags and WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE.inv()
        } else {
            lp.flags = lp.flags or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
        }
        
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            try {
                if (overlayView != null) {
                    wm.updateViewLayout(view, lp)
                }
            } catch (e: Exception) {
                android.util.Log.e("StatusOverlay", "updateViewLayout failed", e)
            }
        }
    }
}
