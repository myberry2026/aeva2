# Hermes Android 测试与维护指南

本文档介绍如何验证和测试 Hermes Android 的 LLM 推理引擎及下载系统。

## 1. LLM 推理接口测试 (Port 8080)

App 启动后会暴露一个 OpenAI 兼容的 API 在 8080 端口。

### 建立连接 (USB 隧道)
在开发机（win 跳板机）执行：
```bash
adb forward tcp:8081 tcp:8080
```

### 验证健康状态
```bash
curl http://localhost:8081/health
```
预期返回：`{"status":"ok","model_loaded":true}`

### 运行压测脚本
使用项目自带的脚本进行性能分析：
```bash
# 在跳板机上运行
bash /tmp/benchmark_llm.sh
```

## 2. 模型下载与断点续传测试

### 下载功能验证
1. 在 App 界面点击 **[Download]**。
2. 观察进度条：总大小应显示为 **2.4GB**。
3. 点击 **[Pause]**：观察 Logcat，确保下载协程立即停止，且 `.tmp` 文件大小锁定。
4. 点击 **[Resume]**：确保进度条从上次停止的位置继续，而不是从 0 开始。

### 手动部署模型
如果网络环境极差，可使用 ADB 手动部署：
```bash
adb push gemma-4-E2B-it.litertlm /sdcard/Android/data/com.hermesandroid.bridge/files/models/
adb shell chmod 666 /sdcard/Android/data/com.hermesandroid.bridge/files/models/gemma-4-E2B-it.litertlm
```

## 3. 常见问题排查 (Troubleshooting)

- **Connection Refused (8081)**: 检查手机端 [Start Server] 按钮是否已点击，以及 `adb forward` 是否成功。
- **Model Load Failed**: 检查 `/sdcard` 空间是否足够（需 >3GB），以及文件权限是否为 `666`。
- **Inference Slow**: 确保在 [Load] 时选择了 `GPU` 后端。如果手机散热不佳，频率可能会下降。

---
*Created by Antigravity AI Agent - 2026-05-12*
