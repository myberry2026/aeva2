#!/usr/bin/env bash
# update_relay.sh - 更新跳板机上的 Python 中转服务器代码并重启

set -e

JUMP_HOST="win"
TOOLS_DIR="tools"
LAUNCHER="scripts/remote_relay_launcher.py"

echo "--- 1. 打包本地 Python 工具库 ---"
tar -czf tools_latest.tar.gz "$TOOLS_DIR"

echo "--- 2. 传输代码到跳板机 ($JUMP_HOST) ---"
scp tools_latest.tar.gz "$JUMP_HOST":/tmp/tools_latest.tar.gz
scp "$LAUNCHER" "$JUMP_HOST":/tmp/remote_relay_launcher.py

echo "--- 3. 远程部署并重启 Relay ---"
ssh "$JUMP_HOST" "
    cd /tmp && 
    tar -xzf tools_latest.tar.gz && 
    pkill -f remote_relay_launcher || true && 
    nohup python3 /tmp/remote_relay_launcher.py > /tmp/relay_v2.log 2>&1 &
"

echo "✓ Relay 已成功更新并重启！"
