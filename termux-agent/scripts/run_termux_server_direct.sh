#!/usr/bin/env bash
# run_termux_server_direct.sh
# 一键部署代码并在手机上以后台守护进程模式启动 Relay Server (直连版)
# 用法: ./scripts/run_termux_server_direct.sh

DEVICE_ID="ZA2232T6XT"
log() { echo -e "\033[0;32m[SERVER-SETUP]\033[0m $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

log "⏳ 等待本地设备 $DEVICE_ID 上线..."
for i in {1..10}; do
    if adb devices | grep -q "$DEVICE_ID.*device$"; then
        log "✅ 设备已就绪!"
        break
    fi
    [ $i -eq 10 ] && log "❌ 等待设备超时，请检查 USB 或网络连接" && exit 1
    sleep 1
done

log "🔌 正在建立端口映射..."
adb -s $DEVICE_ID forward tcp:8765 tcp:8765 || log "⚠️ forward tcp:8765 失败"
adb -s $DEVICE_ID reverse tcp:1234 tcp:1234 || log "⚠️ reverse tcp:1234 失败"

log "📦 正在部署最新 Python 代码到手机..."
./scripts/deploy_direct.sh "$DEVICE_ID" > /dev/null

log "📂 正在同步代码到 Termux 内部存储..."
adb -s $DEVICE_ID shell 'run-as com.termux mkdir -p files/home/phone-vision-memory && run-as com.termux cp -r /data/local/tmp/phone-vision-memory/* files/home/phone-vision-memory/'

log "🚀 正在手机端启动 Relay 守护进程..."
# 调用手机上的 start_daemon_termux.sh 脚本
adb -s $DEVICE_ID shell 'run-as com.termux env PATH=/data/data/com.termux/files/usr/bin bash files/home/phone-vision-memory/scripts/start_daemon_termux.sh'

log "✅ 部署并启动完毕！"
log "🎉 现在你可以脱离电脑，在手机 APP 聊天框里输入 '/task 你的目标' 来唤起 Agent 了。"
