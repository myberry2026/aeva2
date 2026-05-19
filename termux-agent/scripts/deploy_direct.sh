#!/usr/bin/env bash
# scripts/deploy_direct.sh - 为 phone-vision-memory 定制的自动化部署脚本 (直连版)
# 去除跳板机，直接将代码推送到本地连接的 Android 手机

set -e

# --- 配置区 ---
DEVICE_ID=$1                            # 命令行第一个参数作为 DEVICE_ID

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[DEPLOY]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

if [ -z "$DEVICE_ID" ]; then
    DEVICE_ID="ZA2232T6XT"
    log "未指定 DEVICE_ID，使用默认设备: $DEVICE_ID"
fi

log "🚀 开始部署 phone-vision-memory 到本地设备 $DEVICE_ID..."

# 1. 配置 ADB 反向隧道
log "1. 配置 ADB 反向隧道 (Port: 8766)..."
adb -s $DEVICE_ID reverse tcp:8766 tcp:8766 || warn "反向隧道 8766 设置失败，请检查连接"

# 2. 将代码推送到手机中转目录
log "2. 将代码推送到手机中转目录 /data/local/tmp/phone-vision-memory..."

# 创建一个临时目录来准备要推送的文件，避免推送不必要的系统文件
TEMP_DIR=$(mktemp -d)
log "正在本地临时打包代码 (排除无关文件)..."
rsync -a \
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
    ./ "$TEMP_DIR/"

adb -s $DEVICE_ID shell mkdir -p /data/local/tmp/phone-vision-memory
adb -s $DEVICE_ID push "$TEMP_DIR"/. /data/local/tmp/phone-vision-memory/

# 清理临时目录
rm -rf "$TEMP_DIR"

# 3. 运行健康检查 (如果在本地执行环境自检)
log "3. 在本地执行环境自检..."
python3 scripts/health_check.py || warn "⚠️ 健康检查未通过，请检查本地环境。"

success "部署完成！代码已推送到手机。"
log "你可以选择将代码同步到 Termux 中运行。"
