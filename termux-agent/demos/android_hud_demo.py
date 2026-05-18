import time
import subprocess
import os

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

def phone_hud(thought, action, step):
    """【Route A】纯演示版：在手机通知栏更新 Agent 实时状态"""
    title = f"🤖 Agent HUD Demo (Step {step})"
    # 处理特殊字符防止 shell 报错
    safe_thought = thought.replace('"', '').replace("'", "")
    safe_action = str(action).replace('"', '').replace("'", "")
    content = f"THOUGHT: {safe_thought}\\nNEXT: {safe_action}"
    
    # 发送 Android 通知
    run_adb(["shell", "cmd", "notification", "post", "-S", "bigtext", "-t", f'"{title}"', "DemoTag", f'"{content}"'])

def run_standalone_demo():
    print("[*] 正在启动 Android 通知栏 HUD 独立演示...")
    print("[*] 请观察手机/模拟器右上角的通知弹窗。")
    
    demo_steps = [
        {"thought": "发现当前在桌面，准备点击‘设置’图标进行检查。", "action": "Click Settings"},
        {"thought": "已进入设置，现在尝试向下滑动查看更多选项。", "action": "Scroll Down"},
        {"thought": "发现 Wi-Fi 处于连接状态。任务即将完成，准备返回主页。", "action": "Back to Home"}
    ]
    
    for i, step in enumerate(demo_steps, 1):
        print(f"[*] 执行第 {i} 步：{step['action']}")
        phone_hud(step["thought"], step["action"], i)
        # 演示等待
        time.sleep(3)

    print("[*] 演示结束。")

if __name__ == "__main__":
    # 检查 adb
    res = run_adb(["devices"])
    if "device\n" not in res.stdout:
        print("错误：未找到已连接的 Android 设备。")
    else:
        run_standalone_demo()
