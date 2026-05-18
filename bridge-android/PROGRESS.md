# Progress tracking for ActionExecutor.kt fix

## 2026-05-12
- [x] Fix unresolved reference `ACTION_IME_ENTER` in `ActionExecutor.kt`
- [x] **Build Fix**: Resolved `TYPE_APPLICATION_OVERLAY` error by using `TYPE_ACCESSIBILITY_OVERLAY` in `ActionExecutor.kt` and `ScreenReader.kt`.
- [x] **Build Fix**: Resolved `Unresolved label` error in `MessageInputText.kt` using explicit labels.
- [x] **scrcpy Installation**: Successfully installed `scrcpy` via Homebrew on Mac.
- [x] **One-click Script**: Created `scripts/remote_scrcpy.sh` for standalone remote mirroring.
- [x] **Full Integration**: Integrated `scrcpy` + SSH tunneling directly into `run_on_termux.sh`.
- [x] **Verification**: Build passes and deployment script is functional.
- [ ] Update CHANGELOG.md

### Lessons & Learnings
- `AccessibilityWindowInfo` uses `TYPE_ACCESSIBILITY_OVERLAY`, not `TYPE_APPLICATION_OVERLAY`.
- Kotlin explicit labels (`label@`) are safer for nested lambdas in Compose to avoid "Unresolved label" errors.
- Combining multiple SSH port forwards (`-L 5037:... -L 8765:...`) simplifies remote automation toolchains.

## 2026-05-16
- [x] **Fix**: Make `StatusOverlay` auto-show on app open if permission is granted. Previously it only showed upon manually toggling the switch because the switch checked-state was updated before binding the change listener.
- [x] **Fix**: Expanded the dragging area of `StatusOverlay`. Previously only the small `headerRow` captured drag events, limiting dragging to the top-left dot. Extracted the `OnTouchListener` and applied it to both `headerRow` and the entire `container`, enabling dragging from any non-scrollable empty space.

### Lessons & Learnings
- **Android View/Switch listeners**: UI components like `Switch` will invoke `onCheckedChanged` synchronously when `isChecked` is set programmatically. It's important to set the state *after* binding the listener, or explicitly call the desired logic if the setup order requires listener suppression.
- **Android Touch Events**: Touch events bubble up from children to parents. By setting a drag listener on a parent container (`LinearLayout`) that returns `true` for `ACTION_DOWN` but isn't applied to scrolling children (like `ScrollView`), we can achieve full-area dragging without breaking scroll functionality, as long as clickable children also share the drag logic.

## 2026-05-20
- [x] 实现 TTS 语音反馈：任务成功播报 "Task Finished"。
- [x] 实现系统震动反馈：成功（短双震），失败（长单震）。
- [x] 优化反馈策略：应用户要求取消了 "Task Failed" 的语音播报。
- [x] UI 交互：任务结束（触发反馈时）自动调用 `setTouchable(true)`。

### Lessons & Learnings
- **TTS**: `TextToSpeech` requires a delay or lifecycle management to ensure the engine is fully initialized before calling `speak`.
- **Haptics**: `VibrationEffect` provides better control over patterns (e.g., `createWaveform`) compared to the deprecated `vibrate(long)` method.
- **Accessibility**: Using `setTouchable(false)` on overlays is great for "click-through" experiences, but must be paired with explicit state restoration once the user interaction loop completes.

## 2026-05-16 (CPU & Memory Diagnostic / CPU与内存状态诊断)
- [x] **Diagnostic / 状态诊断**: Investigated user report of "CPU explosion" (CPU爆炸) on device `ZA2232T6XT` connected via SSH `win`.
- [x] **Analysis / 深度分析**: Discovered that active CPU usage is very low (~13% total), but the Linux Load Average is extremely high (~17.0).
- [x] **Root Cause / 根本原因**: Identified a massive memory and OpenGL graphics memory leak in `com.hermesandroid.bridge`. The bridge process is consuming **3.5 GB** of RAM, of which **2.74 GB** is graphics memory (`GL mtrack` / `Graphics`). This severe resource starvation causes heavy memory thrashing (Swap is 2.9 GB used) and graphics queue freezes, resulting in UI lockups that look like CPU starvation.
- [x] **Action / 解决方案**: Provided the command to force-stop `com.hermesandroid.bridge` to release the leaked resources and instantly revive the device.

### Lessons & Learnings / 经验与教训
- **Load Average vs. CPU Usage**: On Android/Linux, a high load average does not always mean high CPU computation. When threads are stuck in uninterruptible sleep (`D` state) due to I/O blockages, driver wait, or memory thrashing, it inflates the load average while keeping active CPU utilization low.
- **GL mtrack Leaks**: In vision-based agent bridges, capturing screenshot buffers continuously without proper resource recycling (`Bitmap.recycle()`, `Image.close()`, or hardware buffer releases) leads to massive OpenGL memory leaks (`GL mtrack`), starving the system RAM and inducing severe graphics latency.

