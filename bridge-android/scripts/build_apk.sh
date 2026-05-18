#!/usr/bin/env bash
# build_apk.sh - 尝试本地编译 APK

set -e

BRIDGE_DIR="hermes-android-bridge"
JAR_PATH="$BRIDGE_DIR/gradle/wrapper/gradle-wrapper.jar"

echo "--- 检查 Java 环境 ---"
java -version

echo "--- 检查 Gradle Wrapper ---"
if [ ! -f "$JAR_PATH" ]; then
    echo "修复缺失的 gradle-wrapper.jar..."
    curl -L https://github.com/gradle/gradle/raw/v8.6.0/gradle/wrapper/gradle-wrapper.jar -o "$JAR_PATH"
fi

echo "--- 开始编译 APK ---"
cd "$BRIDGE_DIR"
if ./gradlew assembleDebug; then
    echo "✓ 编译成功: $BRIDGE_DIR/app/build/outputs/apk/debug/app-debug.apk"
else
    echo "✗ 编译失败！"
    echo "提示: 本地环境可能缺少 Android SDK (ANDROID_HOME)。"
    echo "如果没有 SDK，建议使用 install_remote.sh 直接从 GitHub 下载预编译包。"
fi
