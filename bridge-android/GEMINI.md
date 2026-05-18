# hermes-android

Remote Android device control system for [hermes-agent](https://github.com/NousResearch/hermes-agent).

## Project Overview

`hermes-android` enables AI agents to control Android devices remotely. It uses a custom bridge app on the device and a Python-based relay/toolset on the server. The architecture is designed to work behind NATs without port forwarding.

### Key Components

- **Android Bridge App (`hermes-android-bridge/`):**
    - **Language:** Kotlin
    - **Core Technology:** Android `AccessibilityService` for UI inspection and interaction.
    - **Intelligence:** Integrated **LiteRT-LM** for on-device multimodal inference.
    - **Communication:** Connects **out** to the server via WebSocket (remote) or hosts a Ktor HTTP server (local/USB, port 8765).
    - **LLM Server:** Hosts an OpenAI-compatible API on port 8080 (NanoHTTPD) for local inference.
- **Python Toolset (`tools/`):**
    - **`android_tool.py`:** Registers 36 `android_*` tools into the `hermes-agent` registry.
    - **`android_relay.py`:** An `aiohttp` WebSocket relay that bridges HTTP tool calls to the phone.
- **hermes-agent Plugin (`hermes-android-plugin/`):** A wrapper to install the toolset as a `hermes-agent` plugin.

### Architecture

```
Phone (Bridge App) ──WebSocket──> Relay (Python) <──HTTP── Tools (Python) <── hermes-agent
      │
      ├─── OpenAI API (Port 8080) <── On-Device Inference (LiteRT-LM)
      │
      └─── HTTP Server (Port 8765) <── Local/USB Control
```

- **Remote Mode:** Phone connects to the relay via WebSocket using a 6-character pairing code.
- **Local/USB Mode:** Tools can talk directly to the phone's HTTP server (default port 8765) via `adb forward`.

## Building and Running

### Android Bridge App
Requires Android Studio or Gradle.
- **Build APK:** `cd hermes-android-bridge && ./gradlew assembleDebug`
- **Install:** `adb install app/build/outputs/apk/debug/app-debug.apk`

### Python Toolset
Requires Python 3.11+.
- **Install dependencies:** `pip install -e .`
- **Install dev dependencies:** `pip install -e ".[dev]"`
- **Run tests:** `pytest tests/`

### Starting the Relay
The relay is usually started via the `android_setup` tool, but can be managed via `android_relay.py`.
- **Default Port:** 8766

## Development Conventions

### Agent Interaction Patterns (from AGENTS.md)

1.  **Read Before Act:** ALWAYS call `android_read_screen` before tapping. Never guess coordinates.
2.  **Prefer Text over Coordinates:** Use `android_tap_text("Continue")` instead of `android_tap(x=540, y=1200)`.
3.  **Wait After Navigation:** Always call `android_wait` with expected text after launching an app or clicking buttons that trigger loading.
4.  **Confirmation Pattern:** For destructive or financial actions (e.g., Uber, sending money), always report to the user and wait for explicit approval.

### Code Style
- **Android:** Kotlin, follow standard Android architecture components where possible. `ActionExecutor` is the main entry point for UI actions.
- **Python:** Async/await using `aiohttp` for the relay. Tools are generally synchronous wrappers around HTTP calls to the relay/bridge.

### Common Package Names
- Uber: `com.ubercab`
- Bolt: `com.bolt.client`
- WhatsApp: `com.whatsapp`
- Spotify: `com.spotify.music`
- Google Maps: `com.google.android.apps.maps`
- Chrome: `com.android.chrome`
- Gmail: `com.google.android.gm`
- Instagram: `com.instagram.android`
- X/Twitter: `com.twitter.android`

## Key Files
- `README.md`: Main project documentation.
- `AGENTS.md`: Specific guidelines for AI agents using these tools.
- `tools/android_tool.py`: Source of truth for tool definitions.
- `hermes-android-bridge/app/src/main/kotlin/com/hermesandroid/bridge/executor/ActionExecutor.kt`: Core execution logic on Android.
- `PLAN.md`: Roadmap and future vision.
