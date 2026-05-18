#!/usr/bin/env bash
# run_termux_server.sh
# 一键部署代码并在手机上以后台守护进程模式启动 Relay Server
# 用法: ./scripts/run_termux_server.sh

DEVICE_ID="ZA2232T6XT"
log() { echo -e "\033[0;32m[SERVER-SETUP]\033[0m $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

log "📱 正在建立 SSH 隧道..."
adb kill-server 2>/dev/null
ssh -L 5037:localhost:5037 -L 8765:localhost:8765 -N -f win 2>/dev/null

log "⏳ 等待远程设备 $DEVICE_ID 上线..."
for i in {1..10}; do
    if adb devices | grep -q "$DEVICE_ID.*device$"; then
        log "✅ 设备已就绪!"
        break
    fi
    [ $i -eq 10 ] && log "❌ 等待设备超时，请检查 SSH 隧道" && exit 1
    sleep 1
done

log "🔌 正在建立端口映射..."
ssh win "adb -s $DEVICE_ID forward tcp:8765 tcp:8765"
ssh win "adb -s $DEVICE_ID reverse tcp:1234 tcp:1234"

log "📦 正在部署最新 Python 代码到手机..."
./scripts/deploy_local.sh "$DEVICE_ID" > /dev/null
ssh win "adb -s $DEVICE_ID shell 'run-as com.termux mkdir -p files/home/phone-vision-memory && run-as com.termux cp -r /data/local/tmp/phone-vision-memory/* files/home/phone-vision-memory/'"

log "🚀 正在手机端启动 Relay 守护进程..."
# 调用手机上的 start_daemon_termux.sh 脚本
ssh win "adb -s $DEVICE_ID shell 'run-as com.termux env PATH=/data/data/com.termux/files/usr/bin bash files/home/phone-vision-memory/scripts/start_daemon_termux.sh'"

log "✅ 部署并启动完毕！"
log "🎉 现在你可以脱离电脑，在手机 APP 聊天框里输入 '/task 你的目标' 来唤起 Agent 了。"
