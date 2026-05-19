#!/usr/bin/env bash
# deploy_direct.sh - 将本地编译好的 APK 部署到直连手机 (无跳板机)
# 用法: ./scripts/deploy_direct.sh [DEVICE_SERIAL]

set -e

DEVICE_ID=${1:-"ZA2232T6XT"}
LOCAL_APK="hermes-android-bridge/app/build/outputs/apk/debug/app-debug.apk"

if [ ! -f "$LOCAL_APK" ]; then
    echo "✗ 错误: 找不到本地 APK 文件，请先运行 ./scripts/build_local.sh"
    exit 1
fi

echo "--- 1. 直接执行 adb 安装 (目标设备: $DEVICE_ID) ---"
echo "提示: 如果安装失败 (Signature mismatch)，请先手动卸载手机上的旧版本。"
adb -s $DEVICE_ID install -r -t -g "$LOCAL_APK"

echo "--- 2. 启动本地中转网关 (Relay) ---"
# 关闭之前可能正在运行的本地 relay
pkill -f local_relay_launcher || true
# 在后台启动
nohup python3 scripts/local_relay_launcher.py > relay_local.log 2>&1 &
echo "本地网关已在后台启动，日志将输出到 relay_local.log"

echo "--- 3. 建立 USB 隧道并重连 ---"
# 直接将本地机器上的 8766 端口反向映射到手机
adb -s $DEVICE_ID reverse tcp:8766 tcp:8766 || echo "反向映射端口失败，如果使用无线调试，请确保网络通畅"
adb -s $DEVICE_ID shell input tap 600 2130 || true

echo "--- 4. 自动加载模型 ---"
# Wait for app and LLM server to start
sleep 5
# Curl from the phone itself — LLM server runs on the device at localhost:8080
MODEL_PATH=$(adb -s $DEVICE_ID shell curl -s http://127.0.0.1:8080/models 2>/dev/null | python3 -c "import sys,json; models=json.load(sys.stdin).get('models',[]); print(models[0]['path'] if models else '')" 2>/dev/null || echo "")
if [ -n "$MODEL_PATH" ]; then
    echo "加载模型: $MODEL_PATH"
    adb -s $DEVICE_ID shell curl -s -X POST http://127.0.0.1:8080/models/load -H 'Content-Type: application/json' -d '{"path":"'$MODEL_PATH'","backend":"gpu"}'
else
    echo "⚠ 未找到模型文件，请手动加载"
fi

echo "✓ 直连部署完成！手机已连接，本地网关已在后台启动。"
