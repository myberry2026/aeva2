# hermes-android

## 概述
Android app，提供聊天 UI、bridge server、LLM 推理、overlay 悬浮窗。

## 项目结构

- `hermes-android-bridge/` — Android 模块
- `scripts/` — 构建和部署脚本

## 关键文件

| 文件 | 作用 |
|------|------|
| app/.../chat/ChatActivity.kt | 主页面 (Compose)，聊天 UI |
| app/.../chat/ChatViewModel.kt | 聊天逻辑，/task /stop 命令处理 |
| app/.../MainActivity.kt | Settings 页面 (XML Views)，状态轮询 |
| app/.../res/layout/activity_main.xml | Settings 布局 |
| app/.../BridgeApplication.kt | App 入口，启动 BridgeServer(8765) + LlmService(8080) |
| app/.../llm/EmbeddedLlmServer.kt | NanoHTTPD LLM server (8080)，auto-load 模型 |
| app/.../llm/LlmInferenceManager.kt | LiteRT-LM 推理管理器 |
| app/.../llm/LlmService.kt | 前台 Service，启动 EmbeddedLlmServer + 预加载模型 |
| app/.../overlay/StatusOverlay.kt | 悬浮窗 HUD |
| app/.../server/BridgeRouter.kt | Ktor bridge server 路由 (8765) |
| app/.../client/RelayClient.kt | WebSocket 客户端，连接远程 relay |

## 端口

| 端口 | 服务 |
|------|------|
| 8765 | BridgeServer (Ktor) — bridge 控制通道 |
| 8080 | EmbeddedLlmServer (NanoHTTPD) — LLM 推理 |

## Settings UI

- ChatActivity (Compose) → 齿轮图标 → Intent → MainActivity (XML)
- Status 行: a11y, server(8765), relay, auth, termux(8767)
- LLM 行: server(8080), model, 下载/加载按钮
- 每 2 秒 Handler 轮询 updateStatus()（只在 Settings 前台运行）

## ChatViewModel 命令

- `/task <目标>` — POST http://127.0.0.1:8767/task
- `/agent <目标>` — 同 /task
- `/stop` — POST http://127.0.0.1:8767/stop，overlay 提示 + TTS 播报

## 构建部署

```bash
./scripts/build_local.sh    # 编译 APK (gradlew assembleDebug)
./scripts/deploy_local.sh   # 部署: scp → adb install → update_relay → 加载模型
```

deploy_local.sh 模型加载用 `adb shell curl` 在手机上执行，端口 8080。

## LLM 模型

- 文件格式: .litertlm
- 搜索路径: getExternalFilesDir/models, /sdcard/Download, /data/local/tmp
- LlmService 启动时主动预加载模型（不等第一次请求）
- EmbeddedLlmServer 有 auto-load fallback
