import os
import time

# 定义你要显示的文字
title = "Test Agent"
text = "Line 1" + " " * 80 + "\nLine 2" + " " * 150 + "\nLine 3"

print("正在启动持久横幅模式... 按 Ctrl+C 停止")

try:
    while True:
        # 发送通知
        # 注意：普通 adb 命令很难触发不消失的横幅，
        # 我们通过不断重新发布来强制系统认为这是一个需要用户关注的新事件
        cmd = f"adb shell \"cmd notification post -S bigtext -t '{title}' agent_tag '{text}'\""
        os.system(cmd)
        
        # 这里的关键是：我们不使用 expand-notifications (那会拉下整个帘子)
        # 我们只管发，如果你的手机开启了“悬浮通知”权限，它会闪现。
        
        time.sleep(2) # 每 2 秒刷一次，保持它在通知列表顶端
except KeyboardInterrupt:
    print("\n已停止。")
