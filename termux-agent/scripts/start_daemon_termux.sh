#!/data/data/com.termux/files/usr/bin/bash
# 启动 Relay HTTP 守护进程
# 运行后，手机 APP 的 Chat UI 即可通过 /task 指令唤起 Agent

PROJECT_DIR="/data/data/com.termux/files/home/phone-vision-memory"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 错误: 找不到项目目录 $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"
mkdir -p logs

# 清理旧进程（端口 8767 = relay HTTP server）
fuser -k 8767/tcp 2>/dev/null
pkill -9 -f "relay_server.py" 2>/dev/null
sleep 1

echo "🚀 启动 Relay HTTP Server..."
export PATH=/data/data/com.termux/files/usr/bin:$PATH
nohup python relay_server.py > logs/relay_daemon.log 2>&1 &

echo "✅ Relay 守护进程已在后台运行 (PID: $!)"
echo "👉 在手机 APP 聊天框发送 /task 指令即可唤起 Agent"
