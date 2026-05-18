#!/usr/bin/env bash
# deploy_local.sh - 将本地编译好的 APK 部署到远程手机
# 用法: ./scripts/deploy_local.sh [DEVICE_SERIAL]

set -e

DEVICE_ID=${1:-"ZA2232T6XT"}
JUMP_HOST="win"
LOCAL_APK="hermes-android-bridge/app/build/outputs/apk/debug/app-debug.apk"
REMOTE_APK="/tmp/app-debug.apk"

if [ ! -f "$LOCAL_APK" ]; then
    echo "✗ 错误: 找不到本地 APK 文件，请先运行 ./scripts/build_local.sh"
    exit 1
fi

echo "--- 1. 将本地 APK 传输到跳板机 ($JUMP_HOST) ---"
scp "$LOCAL_APK" "$JUMP_HOST":"$REMOTE_APK"

echo "--- 2. 远程执行 adb 安装 (目标设备: $DEVICE_ID) ---"
echo "提示: 如果安装失败 (Signature mismatch)，请先手动卸载手机上的旧版本。"
ssh "$JUMP_HOST" "adb -s $DEVICE_ID install -r -t -g $REMOTE_APK"

echo "--- 3. 自动同步并重启网关 (Relay) ---"
./scripts/update_relay.sh

echo "--- 4. 恢复 USB 隧道并重连 ---"
ssh "$JUMP_HOST" "adb -s $DEVICE_ID reverse tcp:8766 tcp:8766 && adb -s $DEVICE_ID shell input tap 600 2130"

echo "--- 5. 自动加载模型 ---"
# Wait for app and LLM server to start
sleep 5
# Curl from the phone itself — LLM server runs on the device at localhost:8080
MODEL_PATH=$(ssh "$JUMP_HOST" "adb -s $DEVICE_ID shell curl -s http://127.0.0.1:8080/models" 2>/dev/null | python3 -c "import sys,json; models=json.load(sys.stdin).get('models',[]); print(models[0]['path'] if models else '')" 2>/dev/null || echo "")
if [ -n "$MODEL_PATH" ]; then
    echo "加载模型: $MODEL_PATH"
    ssh "$JUMP_HOST" "adb -s $DEVICE_ID shell curl -s -X POST http://127.0.0.1:8080/models/load -H 'Content-Type: application/json' -d '{\"path\":\"$MODEL_PATH\",\"backend\":\"gpu\"}'"
else
    echo "⚠ 未找到模型文件，请手动加载"
fi

echo "✓ 部署完成！手机已重连，网关已更新。"
