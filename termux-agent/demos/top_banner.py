import os
import time

# 模拟系统横幅的样式：顶部、窄长、悬浮
# 这里我们调用你项目里已有的 android_hud_demo 逻辑，但调整它的尺寸和位置
def show_top_banner(title, content):
    # 构造显示的文字
    display_text = f"【{title}】\n{content}"
    
    print(f"正在屏幕顶部创建持久横幅...")
    # 使用项目现有的 android_hud 工具（假设它支持位置参数，或者我们模拟它的行为）
    # 如果没有现成的，我们直接用 adb 模拟一个简单的提示
    os.system(f"adb shell 'while true; do am broadcast -a android.intent.action.MAIN --es text \"{display_text}\"; sleep 3; done' &")

if __name__ == "__main__":
    title = "Test Agent"
    content = "Line 1\nLine 2\nLine 3"
    show_top_banner(title, content)
