package com.hermesandroid.bridge.media

import android.content.Context
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.MediaRecorder
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Handler
import android.os.HandlerThread
import android.util.Base64
import com.hermesandroid.bridge.service.BridgeAccessibilityService
import java.io.File

object ScreenRecorder {
    private var projection: MediaProjection? = null
    private var recorder: MediaRecorder? = null
    private var virtualDisplay: VirtualDisplay? = null
    private val handlerThread = HandlerThread("ScreenRecorder").apply { start() }
    private val handler = Handler(handlerThread.looper)

    fun hasPermission(): Boolean = projection != null

    fun setProjection(p: MediaProjection) {
        projection?.stop()
        projection = p
    }

    /**
     * Record the screen for [durationMs] milliseconds.
     * CRITICAL: Entire recording runs on the HandlerThread via handler.post().
     * MediaRecorder.start()/stop() and Thread.sleep() MUST be on the same thread
     * that created the VirtualDisplay callback handler — NOT on Dispatchers.IO.
     */
    fun record(durationMs: Long = 5000): Map<String, Any?> {
        val service = BridgeAccessibilityService.instance
            ?: return mapOf("success" to false, "message" to "Accessibility service not running")
        
        val proj = projection
        if (proj == null) {
            android.util.Log.e("ScreenRecorder", "MediaProjection is NULL")
            return mapOf("success" to false, "message" to "No MediaProjection. Tap 'Grant Screen Recording' in the app first.")
        }

        val latch = java.util.concurrent.CountDownLatch(1)
        val resultHolder = arrayOf<Map<String, Any?>?>(null)

        handler.post {
            var outputFile: File? = null
            var vd: VirtualDisplay? = null
            var mr: MediaRecorder? = null
            try {
                outputFile = File(service.cacheDir, "screen_record_${System.currentTimeMillis()}.mp4")
                val metrics = service.resources.displayMetrics
                val width = metrics.widthPixels
                val height = metrics.heightPixels
                val density = metrics.densityDpi

                mr = MediaRecorder(service).apply {
                    setVideoSource(MediaRecorder.VideoSource.SURFACE)
                    setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                    setOutputFile(outputFile.absolutePath)
                    setVideoSize(width, height)
                    setVideoEncoder(MediaRecorder.VideoEncoder.H264)
                    setVideoEncodingBitRate(3_000_000)
                    setVideoFrameRate(30)
                    prepare()
                }
                recorder = mr

                // REQUIRED on Android 14+: Register callback BEFORE creating VirtualDisplay
                proj.registerCallback(object : MediaProjection.Callback() {
                    override fun onStop() {
                        super.onStop()
                        android.util.Log.i("ScreenRecorder", "MediaProjection stopped")
                    }
                }, handler)

                android.util.Log.i("ScreenRecorder", "Creating VirtualDisplay...")
                vd = proj.createVirtualDisplay(
                    "ScreenRecorder", width, height, density,
                    DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                    mr.surface, null, handler
                )
                virtualDisplay = vd

                android.util.Log.i("ScreenRecorder", "Starting MediaRecorder...")
                mr.start()

                Thread.sleep(durationMs)

                android.util.Log.i("ScreenRecorder", "Stopping recording...")
                mr.stop()
                
                val bytes = outputFile.readBytes()
                val base64Video = Base64.encodeToString(bytes, Base64.NO_WRAP)

                resultHolder[0] = mapOf(
                    "success" to true,
                    "data" to mapOf("video" to base64Video, "durationMs" to durationMs)
                )
            } catch (e: Exception) {
                android.util.Log.e("ScreenRecorder", "Capture failed", e)
                resultHolder[0] = mapOf("success" to false, "message" to "Capture failed: ${e.message}")
            } finally {
                try { vd?.release() } catch (_: Exception) {}
                try { mr?.release() } catch (_: Exception) {}
                outputFile?.delete()
                latch.countDown()
            }
        }

        latch.await(durationMs + 5000, java.util.concurrent.TimeUnit.MILLISECONDS)
        return resultHolder[0] ?: mapOf("success" to false, "message" to "Recording timed out")
    }

    fun release() {
        handlerThread.quitSafely()
    }
}
