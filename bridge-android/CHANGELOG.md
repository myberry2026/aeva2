# CHANGELOG

## [Unreleased] - 2026-05-16

### Voice & UI Feedback
- **TTS Feedback**: 取消任务失败时的语音播报 ("Task Failed")，保持成功播报及震动反馈。
- **Status Overlay Optimization**: 优化 StatusOverlay，在任务结束时自动恢复 UI 交互。
- **State Monitoring**: 实现了任务状态监测的边缘触发反馈机制。

### Fixed - UI Behavior
- **Status Overlay Initialization**: Fixed an issue in `MainActivity.kt` where the `StatusOverlay` (悬浮窗) required a manual toggle to show up after launching the app. It now automatically displays upon app launch if the overlay permission has been granted.
- **Status Overlay Dragging**: Fixed an issue where the overlay could only be dragged by grabbing the small top-left dot. Expanded the drag area to cover the entire non-scrollable background (`container`) and the full header row, making repositioning much easier.

## [Previous] - 2026-05-12

### Added - Remote Mirroring & Debugging Tooling
- **scrcpy Integration**: Integrated `scrcpy` (Screen Copy) for real-time remote phone mirroring on Mac.
- **Remote Automation Script**: Added `scripts/remote_scrcpy.sh` to automate SSH tunneling (ADB port 5037) for accessing phones connected via Windows jump-boxes.
- **One-Click Toolchain**: Integrated `scrcpy` startup and SSH tunneling directly into `run_on_termux.sh`, creating a unified developer workflow for remote debugging.

### Fixed - Compilation & Build Stability
- **Build Fix (Accessibility)**: Resolved `Unresolved reference 'TYPE_APPLICATION_OVERLAY'` in `ActionExecutor.kt` and `ScreenReader.kt` by using correct `AccessibilityWindowInfo.TYPE_ACCESSIBILITY_OVERLAY` constant.
- **Build Fix (Compose)**: Fixed `Unresolved label` error in `MessageInputText.kt` by implementing explicit labels (`@onPressLabel`) for nested lambdas.
- **Dependency**: Ensured `scrcpy` is installed on developer Mac environment.

## [Previous] - 2026-05-12
### Changed - UI Style Unification & Navigation
- **Settings Page Styling**: Stripped legacy custom "hacker" styles (monospace, orange highlights) from `activity_main.xml`. Adopted standard Android system attributes (`?android:attr/textColorPrimary`) and `Theme.DeviceDefault.NoActionBar` for native adaptive Light/Dark mode consistency.
- **Settings Navigation**: Added a Top Bar with a Back Button to `MainActivity` allowing seamless return to the `ChatActivity` home page.

### Fixed
- **ActionExecutor**: Fixed compilation error `Unresolved reference 'ACTION_IME_ENTER'` by using `AccessibilityNodeInfo.AccessibilityAction.ACTION_IME_ENTER.id`.
- **Resource Linking**: Fixed missing `@color/card_bg`, `@color/border`, and `@color/input_bg` by adding aliases in `colors.xml`.
- **Rebranding Sync**: Renamed styles in `themes.xml` to `Theme.HermesBridge.Day/Night` to match code references in `MainActivity.kt`.
