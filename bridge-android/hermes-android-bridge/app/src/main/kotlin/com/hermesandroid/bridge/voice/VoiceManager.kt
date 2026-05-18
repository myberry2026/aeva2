package com.hermesandroid.bridge.voice

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.media.AudioManager
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import java.util.Locale

object VoiceManager {
    private const val TAG = "VoiceManager"
    private var speechRecognizer: SpeechRecognizer? = null
    private var audioManager: AudioManager? = null
    private var originalNotificationVolume: Int = -1
    private var originalSystemVolume: Int = -1
    private var isContinuous: Boolean = false
    private var savedContext: Context? = null
    private val handler = android.os.Handler(android.os.Looper.getMainLooper())
    private var destroyRunnable: Runnable? = null

    interface VoiceCallback {
        fun onPartialResult(text: String)
        fun onFinalResult(text: String)
        fun onError(error: String)
    }

    private var currentCallback: VoiceCallback? = null

    private fun muteSounds(context: Context) {
        try {
            if (audioManager == null) {
                audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            }
            if (originalNotificationVolume == -1) {
                originalNotificationVolume = audioManager?.getStreamVolume(AudioManager.STREAM_NOTIFICATION) ?: 0
                originalSystemVolume = audioManager?.getStreamVolume(AudioManager.STREAM_SYSTEM) ?: 0
            }
            audioManager?.setStreamVolume(AudioManager.STREAM_NOTIFICATION, 0, 0)
            audioManager?.setStreamVolume(AudioManager.STREAM_SYSTEM, 0, 0)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to mute sounds", e)
        }
    }

    private fun restoreSounds() {
        try {
            if (originalNotificationVolume != -1) {
                audioManager?.setStreamVolume(AudioManager.STREAM_NOTIFICATION, originalNotificationVolume, 0)
                audioManager?.setStreamVolume(AudioManager.STREAM_SYSTEM, originalSystemVolume, 0)
                originalNotificationVolume = -1
                originalSystemVolume = -1
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to restore sounds", e)
        }
    }

    fun startListening(context: Context, callback: VoiceCallback?, continuous: Boolean = false) {
        currentCallback = callback
        isContinuous = continuous
        savedContext = context.applicationContext

        muteSounds(context)

        handler.post {
            doStartListening(context)
        }
    }

    private fun doStartListening(context: Context) {
        try {
            // Cancel any pending destroy from a previous stopListening()
            destroyRunnable?.let { handler.removeCallbacks(it) }
            destroyRunnable = null

            if (speechRecognizer != null) {
                speechRecognizer?.destroy()
                speechRecognizer = null
            }

            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context)

            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toString())
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                putExtra("android.speech.extra.DICTATION_MODE", true)
            }

            speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) { Log.i(TAG, "onReadyForSpeech") }
                override fun onBeginningOfSpeech() { Log.i(TAG, "onBeginningOfSpeech") }
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() { Log.i(TAG, "onEndOfSpeech") }

                override fun onError(error: Int) {
                    val message = when (error) {
                        SpeechRecognizer.ERROR_AUDIO -> "Audio error"
                        SpeechRecognizer.ERROR_CLIENT -> "Client error"
                        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Permission error"
                        SpeechRecognizer.ERROR_NETWORK -> "Network error"
                        SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timeout"
                        SpeechRecognizer.ERROR_NO_MATCH -> "No match"
                        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Busy"
                        SpeechRecognizer.ERROR_SERVER -> "Server error"
                        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "Speech timeout"
                        else -> "Unknown error ($error)"
                    }
                    Log.e(TAG, "Error: $message")
                    if (isContinuous) {
                        handler.postDelayed({
                            if (isContinuous) {
                                savedContext?.let { doStartListening(it) }
                            }
                        }, 100)
                    } else {
                        currentCallback?.onError(message)
                    }
                }

                override fun onResults(results: Bundle?) {
                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    val text = matches?.get(0) ?: ""
                    Log.i(TAG, "onResults: $text")
                    if (text.isNotEmpty()) {
                        currentCallback?.onFinalResult(text)
                    } else {
                        currentCallback?.onFinalResult("")
                    }
                    if (isContinuous) {
                        handler.postDelayed({
                            if (isContinuous) {
                                savedContext?.let { doStartListening(it) }
                            }
                        }, 100)
                    }
                }

                override fun onPartialResults(partialResults: Bundle?) {
                    val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    val text = matches?.get(0) ?: ""
                    if (text.isNotEmpty()) {
                        Log.i(TAG, "onPartialResults: $text")
                        currentCallback?.onPartialResult(text)
                    }
                }

                override fun onEvent(eventType: Int, params: Bundle?) {}
            })

            speechRecognizer?.startListening(intent)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize SpeechRecognizer", e)
            if (!isContinuous) {
                currentCallback?.onError(e.message ?: "Init failed")
            }
        }
    }

    fun stopListening() {
        isContinuous = false
        restoreSounds()
        handler.post {
            try {
                speechRecognizer?.stopListening()
                // Delay destroy to let onResults fire first.
                // doStartListening() cancels this if called before it fires.
                val runnable = Runnable {
                    try {
                        speechRecognizer?.destroy()
                        speechRecognizer = null
                    } catch (e: Exception) {
                        Log.e(TAG, "Error destroying recognizer", e)
                    }
                }
                destroyRunnable = runnable
                handler.postDelayed(runnable, 500)
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping listener", e)
            }
        }
    }
}
