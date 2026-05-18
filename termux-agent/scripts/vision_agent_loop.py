import subprocess
import time
import base64
import requests
import json
import os
import re

def log(msg):
    print(f"[*] {msg}")

# --- 模拟器工具集 ---

def adb_click_text(text):
    log(f"执行点击: '{text}'")
    try:
        subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/ui.xml"], capture_output=True)
        xml_content = subprocess.run(["adb", "shell", "cat", "/sdcard/ui.xml"], capture_output=True, text=True).stdout
        pattern = f'text="{text}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
        match = re.search(pattern, xml_content, re.IGNORECASE)
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            subprocess.run(["adb", "shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2)])
            return True
        return False
    except: return False

def adb_scroll_down():
    log("执行动作: 向下滚动")
    subprocess.run(["adb", "shell", "input", "swipe", "500", "1500", "500", "500", "500"])
    return True

def adb_back():
    log("执行动作: 返回")
    subprocess.run(["adb", "shell", "input", "keyevent", "4"])
    return True

# --- Agent 核心逻辑 ---

def agent_step(image_path, goal, history):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = f"""
你是一个 Android 自动驾驶 Agent。
任务目标: {goal}

可用的工具:
1. {{"tool": "click", "text": "按钮文字"}} - 点击屏幕上的文字。
2. {{"tool": "scroll_down"}} - 找不到目标时向下滚动。
3. {{"tool": "finish", "reason": "原因"}} - 当你看到目标信息（如 Android 版本号）时结束任务。

当前历史动作: {history}

请根据当前的截图，决定下一步动作。必须只返回 JSON。
"""

    payload = {
        "model": "gemma4:latest",
        "prompt": prompt,
        "images": [img_b64],
        "format": "json",
        "stream": False
    }

    try:
        r = requests.post(url, json=payload, timeout=90)
        return json.loads(r.json().get("response"))
    except Exception as e:
        log(f"AI 响应解析失败: {e}")
        return None

def main():
    goal = "在设置中找到 'About phone' 或 'About device' 并点击它，查看 Android 版本信息。"
    max_steps = 5
    history = []
    
    # 初始状态：确保在设置首页
    log("启动智能体循环...")
    subprocess.run(["adb", "shell", "am", "start", "-a", "android.settings.SETTINGS"])
    time.sleep(3)

    for step in range(max_steps):
        log(f"\n=== 第 {step+1} 步 ===")
        
        # 1. 截图
        screenshot = f"agent_step_{step}.png"
        subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=open(screenshot, "wb"))
        
        # 2. 问 AI 该干嘛
        decision = agent_step(screenshot, goal, history)
        if not decision: 
            log("AI 罢工了。")
            break
            
        log(f"AI 决策: {decision}")
        history.append(decision)

        # 3. 执行动作
        tool = decision.get("tool")
        if tool == "click":
            text = decision.get("text")
            if not adb_click_text(text):
                log(f"点击失败，屏幕上可能没找到 '{text}'")
        elif tool == "scroll_down":
            adb_scroll_down()
        elif tool == "finish":
            log(f"任务完成！原因: {decision.get('reason')}")
            break
        
        time.sleep(3) # 等待 UI 刷新

if __name__ == "__main__":
    main()
