#!/usr/bin/env bash
# run_on_termux.sh - 深度自动化版
# 实现了 Mac -> Win -> Phone 的全链路透传

INSTRUCTION=$1
DEVICE_ID="ZA2232T6XT"
log() { echo -e "\033[0;34m[REMOTE]\033[0m $1"; }

# 准备本地日志目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_LOGS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/logs"
mkdir -p "$LOCAL_LOGS_DIR"

if [ -z "$INSTRUCTION" ]; then
    echo "❌ 使用方法: $0 \"你的指令\""
    exit 1
fi

# 1. 建立 SSH 隧道 & 端口映射
log "📱 正在建立 SSH 隧道..."
adb kill-server 2>/dev/null
ssh -L 5037:localhost:5037 -L 8765:localhost:8765 -N -f win 2>/dev/null

# 等待 ADB 设备上线 (最多等 10 秒)
log "⏳ 等待远程设备 $DEVICE_ID 上线..."
for i in {1..10}; do
    if adb devices | grep -q "$DEVICE_ID.*device$"; then
        log "✅ 设备已就绪!"
        break
    fi
    [ $i -eq 10 ] && log "❌ 等待设备超时，请检查 SSH 隧道" && exit 1
    sleep 1
done

log "🔌 正在建立全链路端口映射 (Bridge & LLM)..."
ssh win "adb -s $DEVICE_ID forward tcp:8765 tcp:8765"
ssh win "adb -s $DEVICE_ID reverse tcp:1234 tcp:1234"

# 2. 部署代码
log "📦 正在部署最新代码到手机..."
./scripts/deploy_local.sh "$DEVICE_ID" > /dev/null
ssh win "adb -s $DEVICE_ID shell 'run-as com.termux mkdir -p files/home/phone-vision-memory && run-as com.termux cp -r /data/local/tmp/phone-vision-memory/* files/home/phone-vision-memory/'"

# 3. 实时日志流 & 后台同步
TERMUX_BASH="/data/data/com.termux/files/usr/bin/bash"

log "📺 开启实时日志流..."
# 先确保手机端日志目录存在
ssh win "adb -s $DEVICE_ID shell 'run-as com.termux mkdir -p files/home/phone-vision-memory/logs'"

# 3a. 后台实时 tail -f 日志到终端 stdout
ssh win "adb -s $DEVICE_ID shell 'run-as com.termux $TERMUX_BASH -c \"
    cd /data/data/com.termux/files/home/phone-vision-memory
    while true; do
        LATEST=\$(ls -dt logs/run_* 2>/dev/null | head -n 1)
        if [ -f \\\"\$LATEST/agent_debug.log\\\" ]; then
            tail -n 0 -f \\\"\$LATEST/agent_debug.log\\\"
            break
        fi
        sleep 0.5
    done
\"'" &
TAIL_PID=$!

# 3b. 后台定时同步：每 5 秒把手机上最新 run_* 目录的所有文件(含截图)拉到本地
"$SCRIPT_DIR/sync_logs.sh" "$DEVICE_ID" "$LOCAL_LOGS_DIR" loop &
SYNC_PID=$!
log "📂 后台同步已启动 (每5s增量同步截图和日志到本地)"

# --- 清理陷阱 (Trap) ---
# 无论脚本是正常结束，还是被 Ctrl+C 中断，都会执行此清理逻辑
cleanup() {
    log "🧹 执行清理收尾工作..."
    # 停止本地后台进程
    kill $TAIL_PID 2>/dev/null
    kill $SYNC_PID 2>/dev/null
    
    # 强杀手机里遗留的 tail 和死循环，防止端口占用和内存泄漏
    ssh win "adb -s $DEVICE_ID shell 'run-as com.termux pkill -f \"agent_debug.log\"'" 2>/dev/null
    ssh win "adb -s $DEVICE_ID shell 'run-as com.termux pkill -f \"tail\"'" 2>/dev/null
    
    pkill -f "ssh -L 5037:localhost:5037"
    
    log "📥 最终同步完整日志目录..."
    "$SCRIPT_DIR/sync_logs.sh" "$DEVICE_ID" "$LOCAL_LOGS_DIR" once

    LATEST_LOCAL=$(ls -dt "$LOCAL_LOGS_DIR"/run_* 2>/dev/null | head -n 1)
    if [ -n "$LATEST_LOCAL" ]; then
        FILE_COUNT=$(find "$LATEST_LOCAL" -type f | wc -l | tr -d ' ')
        log "✅ 完整日志已保存到: $LATEST_LOCAL ($FILE_COUNT 个文件)"
    else
        log "⚠️ 未找到日志目录。"
    fi
    log "✅ 运行结束。"
}
trap cleanup EXIT INT TERM

# 4. 正式启动 Agent
log "🚀 启动 Agent..."
ssh win "adb -s $DEVICE_ID shell 'run-as com.termux env PATH=/data/data/com.termux/files/usr/bin bash files/home/phone-vision-memory/scripts/start_agent_termux.sh \"$INSTRUCTION\"'"
