#!/usr/bin/env bash
# scripts/deploy_local.sh - 为 phone-vision-memory 定制的自动化部署脚本
# 参照 bridge-android 架构，支持代码同步、设备推送及隧道配置

set -e

# --- 配置区 ---
JUMP_HOST=${JUMP_HOST:-"win"}          # 跳板机 (在 ~/.ssh/config 中定义或使用 IP)
REMOTE_PATH="~/phone-vision-memory"     # 跳板机工作目录
DEVICE_ID=$1                            # 命令行第一个参数作为 DEVICE_ID

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[DEPLOY]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

log "🚀 开始部署 phone-vision-memory 到 $JUMP_HOST..."

# 1. 同步本地 Python 代码到跳板机
log "1. 同步本地代码到跳板机..."
# 使用 rsync 排除无关文件，并使用 --del 保持远端同步
rsync -avz --del \
    --exclude '.git/' \
    --exclude 'logs/' \
    --exclude 'data/' \
    --exclude '**/__pycache__/' \
    --exclude '.env' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    --exclude '.*_env/' \
    --exclude 'venv/' \
    --exclude 'env/' \
    ./ "$JUMP_HOST":"$REMOTE_PATH"



# 2. 如果检测到设备，则执行 ADB 推送和隧道配置
if [ -n "$DEVICE_ID" ]; then
    log "2. 检测到目标设备: $DEVICE_ID，执行手机侧部署..."
    
    # 建立反向隧道 (用于手机端 Agent 连接 PC 端的 Relay Server)
    log "3. 配置 ADB 反向隧道 (Port: 8766)..."
    ssh "$JUMP_HOST" "adb -s $DEVICE_ID reverse tcp:8766 tcp:8766"
    
    # 将代码推送到手机 /data/local/tmp (作为中转)
    log "4. 将代码推送到手机中转目录..."
    ssh "$JUMP_HOST" "adb -s $DEVICE_ID shell mkdir -p /data/local/tmp/phone-vision-memory"
    ssh "$JUMP_HOST" "cd $REMOTE_PATH && adb -s $DEVICE_ID push . /data/local/tmp/phone-vision-memory/"
    
    # 针对 Termux 环境的特别处理 (如果需要)
    # warn "提示: 若需在 Termux 运行，请在手机执行: cp -r /data/local/tmp/phone-vision-memory ~/"
else
    warn "未指定 DEVICE_ID，跳过手机侧推送。仅完成跳板机代码同步。"
fi

# 3. 运行健康检查
log "5. 在跳板机执行环境自检..."
ssh "$JUMP_HOST" "cd $REMOTE_PATH && python3 scripts/health_check.py || echo '⚠️ 健康检查未通过，请检查环境。'"

success "部署完成！"
log "接下来你可以："
log "  - 在跳板机运行: ssh $JUMP_HOST 'cd $REMOTE_PATH && python3 humanoid_agent.py \"你的指令\"'"
log "  - 或在手机 Termux 运行同步后的代码。"
