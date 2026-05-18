import os
import time

# 文字内容
text = "Line 1                                                                            \nLine 2                                                                                                                                                  \nLine 3"

print("正在启动【强行弹出】模式...")
print("这个模式会不断发送系统级提示，尝试在不下拉通知栏的情况下弹出横幅。")

try:
    while True:
        # 使用 am broadcast 模拟一个系统消息弹窗（Toast 或 Hint）
        # 这种方式通常会直接在屏幕上显示一个小横块
        cmd = f'adb shell "am broadcast -a android.intent.action.MAIN --es text \'{text}\'"'
        os.system(cmd)
        
        # 同时发送一个带图标的通知，但不做下拉动作
        os.system(f"adb shell \"cmd notification post -S bigtext -t 'Agent Message' tag '{text}'\"")
        
        time.sleep(3)
except KeyboardInterrupt:
    print("\n停止运行。")
