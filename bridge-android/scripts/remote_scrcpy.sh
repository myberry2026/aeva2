#!/bin/bash

# ==========================================
# 配置区域: 请填入你的 Windows 跳板机信息
# ==========================================
WIN_USER="YOUR_WINDOWS_USERNAME"
WIN_IP="YOUR_WINDOWS_IP"
# ==========================================

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 准备启动远程 scrcpy (跳板机方案)...${NC}"

# 1. 清理本地 ADB
echo -e "${BLUE}🧹 清理本地 ADB server 防止端口冲突...${NC}"
adb kill-server

# 2. 建立 SSH 隧道
echo -e "${BLUE}🌉 正在建立 SSH 隧道到 $WIN_IP...${NC}"
echo -e "${BLUE}提示: 如果你没配置 SSH Key，可能需要输入两次密码。${NC}"

# 建立隧道 (-L 转发，-N 不执行命令，-f 后台运行)
ssh -L 5037:localhost:5037 -N -f "$WIN_USER@$WIN_IP"

# 等待隧道稳定
sleep 2

# 检查 5037 是否被转发
if lsof -i tcp:5037 > /dev/null; then
    echo -e "${GREEN}✅ SSH 隧道建立成功!${NC}"
else
    echo -e "${RED}❌ 隧道建立失败。${NC}"
    echo "请尝试手动运行: ssh -L 5037:localhost:5037 $WIN_USER@$WIN_IP"
    exit 1
fi

# 3. 启动 scrcpy
echo -e "${BLUE}📱 正在拉取远程手机屏幕...${NC}"
echo -e "${BLUE}配置: 1024px 缩放 | 2M 码率 | 30 FPS (优化网络延迟)${NC}"

# 启动 scrcpy
# -m: max size, -b: bitrate
scrcpy -m 1024 -b 2M --max-fps 30 --window-title "Remote Phone ($WIN_IP)"

# 4. 清理隧道
echo -e "${BLUE}🛑 scrcpy 已关闭，正在清理 SSH 隧道...${NC}"
pkill -f "ssh -L 5037:localhost:5037"
echo -e "${GREEN}✨ 完成。${NC}"
