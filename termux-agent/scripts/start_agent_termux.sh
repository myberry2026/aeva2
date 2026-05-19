#!/data/data/com.termux/files/usr/bin/bash
# phone-vision-memory 一键启动脚本
# 使用说明: ./start_agent.sh "你的指令"

PROJECT_DIR="/data/data/com.termux/files/home/phone-vision-memory"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 错误: 找不到项目目录 $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# 核心配置：使用 Bridge 端侧控制 + GALLERY 端侧模型
export CONTROL_BACKEND=bridge
export BRIDGE_TOKEN=9RG2VK
export BRIDGE_URL=http://127.0.0.1:8765
export AGENT_MODEL=GALLERY
export GALLERY_URL=http://127.0.0.1:8080

echo "🤖 Agent 启动中 (端侧模式)..."
exec python -u humanoid_agent.py "$@"
