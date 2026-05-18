#!/bin/bash

# setup_device_automation.sh
# 自动化配置 Android 设备环境：安装 APK、设置输入法、开启无障碍服务
# 用法: ./setup_device_automation.sh <DEVICE_ID>

SERIAL=$1
if [ -z "$SERIAL" ]; then
    echo "Usage: $0 <SERIAL>"
    exit 1
fi

ADB="adb -s $SERIAL"

echo "=== 1. 安装必要 APK ==="
# 假设 APK 在当前目录或 vendor 目录下
APK_DIR="./vendor"
if [ ! -d "$APK_DIR" ]; then
    APK_DIR="../vendor"
fi

# 安装 ADBKeyboard
if [ -f "$APK_DIR/ADBKeyboard.apk" ]; then
    echo "Installing ADBKeyboard..."
    $ADB install -r "$APK_DIR/ADBKeyboard.apk"
else
    echo "Warning: ADBKeyboard.apk not found in $APK_DIR"
fi

# 安装 AppiumSettings
if [ -f "$APK_DIR/AppiumSettings.apk" ]; then
    echo "Installing AppiumSettings..."
    $ADB install -r "$APK_DIR/AppiumSettings.apk"
else
    echo "Warning: AppiumSettings.apk not found in $APK_DIR"
fi

echo "=== 2. 配置输入法 (IME) ==="
ADB_IME="com.android.adbkeyboard/.AdbIME"
$ADB shell ime enable $ADB_IME
$ADB shell ime set $ADB_IME
echo "IME set to $ADB_IME"

echo "=== 3. 开启无障碍服务 (Accessibility) ==="
BRIDGE_SERVICE="com.bridgeandroid.bridge/.service.BridgeAccessibilityService"
AUTOJS_SERVICE="org.autojs.autoxjs.v7/com.stardust.autojs.core.accessibility.AccessibilityService"
MOBILERUN_SERVICE="com.mobilerun.portal/.service.MobilerunAccessibilityService"

# 获取当前已开启的服务，避免覆盖其他的
CURRENT_SERVICES=$($ADB shell settings get secure enabled_accessibility_services | tr -d '\r')

if [[ "$CURRENT_SERVICES" == "null" || -z "$CURRENT_SERVICES" ]]; then
    NEW_SERVICES="$BRIDGE_SERVICE:$AUTOJS_SERVICE:$MOBILERUN_SERVICE"
else
    # 检查是否已包含，不包含则追加
    NEW_SERVICES="$CURRENT_SERVICES"
    [[ "$CURRENT_SERVICES" != *"$BRIDGE_SERVICE"* ]] && NEW_SERVICES="$NEW_SERVICES:$BRIDGE_SERVICE"
    [[ "$CURRENT_SERVICES" != *"$AUTOJS_SERVICE"* ]] && NEW_SERVICES="$NEW_SERVICES:$AUTOJS_SERVICE"
    [[ "$CURRENT_SERVICES" != *"$MOBILERUN_SERVICE"* ]] && NEW_SERVICES="$NEW_SERVICES:$MOBILERUN_SERVICE"
fi

$ADB shell settings put secure enabled_accessibility_services "$NEW_SERVICES"
$ADB shell settings put secure accessibility_enabled 1
echo "Accessibility services enabled: $NEW_SERVICES"

echo "=== 4. 启动 Bridge ==="
$ADB shell am start -n com.bridgeandroid.bridge/.MainActivity
echo "Bridge launched."

echo "=== 配置完成！ ==="

# --- 温馨提示 ---
# 如果你在运行过程中发现 Termux 报错 "Operation not permitted"
# 那是因为 Android 系统把 Termux 关了禁闭。
# 解决办法：手动在手机上打开一次 Termux App 即可恢复联网！
