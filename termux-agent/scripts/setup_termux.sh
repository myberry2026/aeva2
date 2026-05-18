#!/usr/bin/env bash
# setup_termux.sh — 在 Termux 中安装 phone-vision-memory 的依赖
# 用法: 在手机 Termux 中运行此脚本
set -e

echo "=== Termux 环境初始化 ==="

# 基础包
pkg update -y
pkg install -y python python-pip git

# Pillow 需要的系统库
pkg install -y libjpeg-turbo zlib freetype

# Python 依赖
pip install --upgrade pip
pip install requests Pillow websockets

echo ""
echo "=== 验证安装 ==="
python -c "import requests, PIL, websockets; print('OK: all deps loaded')"

echo ""
echo "=== 设置环境变量（加入 ~/.bashrc）==="

PROFILE="$HOME/.bashrc"
touch "$PROFILE"

add_env() {
    local key="$1" val="$2"
    if ! grep -q "^export $key=" "$PROFILE" 2>/dev/null; then
        echo "export $key=\"$val\"" >> "$PROFILE"
        echo "  + $key=$val"
    else
        echo "  ~ $key already set"
    fi
}

add_env CONTROL_BACKEND "bridge"
add_env BRIDGE_URL "http://localhost:8765"
add_env BRIDGE_TOKEN ""
add_env GALLERY_URL "http://localhost:8080"
add_env AGENT_MODEL "GALLERY"
add_env WS_PORT "8766"

source "$PROFILE"

echo ""
echo "=== 完成 ==="
echo "接下来:"
echo "  1. 确保 bridge-android 和 gallery app 已安装并运行"
echo "  2. cd phone-vision-memory"
echo "  3. python humanoid_agent.py \"打开设置\""
