# Progress, Lessons and Learnings

## 2026-05-18
- [New Feature] 开发了基于本地直连（无需 jump machine）的 Android app 部署脚本。
  - 新增 `bridge-android/scripts/local_relay_launcher.py`: 用于在本地 Mac 上直接启动 Python 中转网关（Relay）。
  - 新增 `bridge-android/scripts/deploy_direct.sh`: 将 `build_local.sh` 编译好的 APK 直接通过本地 `adb` 安装到手机，并在后台启动本地网关以及进行 `adb reverse` 端口反向映射，从而替代原先依赖跳板机的流程。
- [New Feature] 开发了基于本地直连的 `termux-agent` 部署脚本。
  - 新增 `termux-agent/scripts/deploy_direct.sh`: 直接利用本地 `adb` 反向映射并将 Python 代码传输到手机。
  - 新增 `termux-agent/scripts/run_termux_server_direct.sh`: 彻底剔除 SSH tunnel 依赖，通过本地 `adb` 完成代码部署和 Termux Relay 服务拉起。
- [Documentation] 翻译并新增了 `termux-agent/CASES_ENGLISH.md`，并将 README 中的参考链接指向英文版。
