#!/usr/bin/env bash
# build_local.sh - 使用本地 SDK 编译 APK

set -e

# 设置本地 Android SDK 路径
export ANDROID_HOME="/Users/a84513/Library/Android/sdk"
export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
BRIDGE_DIR="hermes-android-bridge"
JAR_PATH="$BRIDGE_DIR/gradle/wrapper/gradle-wrapper.jar"

echo "--- 检查 Java 环境 ---"
java -version

echo "--- 检查 SDK 路径 ---"
if [ ! -d "$ANDROID_HOME" ]; then
    echo "✗ 错误: 找不到 Android SDK 路径: $ANDROID_HOME"
    exit 1
fi

echo "--- 检查 Gradle Wrapper ---"
if [ ! -f "$JAR_PATH" ]; then
    echo "修复缺失的 gradle-wrapper.jar..."
    curl -L https://github.com/gradle/gradle/raw/v8.10.2/gradle/wrapper/gradle-wrapper.jar -o "$JAR_PATH"
fi

echo "--- 开始编译 APK ---"
cd "$BRIDGE_DIR"
./gradlew assembleDebug

echo ""
echo "✓ 编译成功！"
echo "APK 位置: $BRIDGE_DIR/app/build/outputs/apk/debug/app-debug.apk"
