#!/usr/bin/env bash
# install_remote.sh - 下载、中转并远程安装 APK
# 用法: ./scripts/install_remote.sh [DEVICE_SERIAL]

set -e

DEVICE_ID=${1:-"ZA2232T6XT"}
JUMP_HOST="win"
APK_URL="https://github.com/raulvidis/hermes-android/releases/download/latest-build/app-debug.apk"
LOCAL_APK="/tmp/app-debug.apk"
REMOTE_APK="/tmp/app-debug.apk"

echo "--- 1. 从 GitHub 下载最新 APK ---"
curl -L "$APK_URL" -o "$LOCAL_APK"

echo "--- 2. 将 APK 传输到跳板机 ($JUMP_HOST) ---"
scp "$LOCAL_APK" "$JUMP_HOST":"$REMOTE_APK"

echo "--- 3. 远程执行 adb 安装 (目标设备: $DEVICE_ID) ---"
echo "请确保手机已亮屏，并准备好点击 '允许安装' 弹窗..."
ssh "$JUMP_HOST" "adb -s $DEVICE_ID install -r -t -g $REMOTE_APK"

echo "✓ 安装完成！请在手机上打开 'Hermes Bridge' App 进行配置。"
