import subprocess
import time
import base64
import requests
import json
import os
import re

def log(msg):
    print(f"[*] {msg}")

# --- 定义 AI 可以调用的“工具”函数 ---

def adb_click_text(text):
    """通过文字内容点击屏幕"""
    log(f"执行工具: 点击文字 '{text}'")
    # 简单的实现：先 dump UI，找坐标，再点击
    try:
        subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/ui.xml"], capture_output=True)
        xml_content = subprocess.run(["adb", "shell", "cat", "/sdcard/ui.xml"], capture_output=True, text=True).stdout
        
        # 匹配 text="文字" 及其之后的 bounds="[x,y][x,y]"
        pattern = f'text="{text}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
        match = re.search(pattern, xml_content)
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            subprocess.run(["adb", "shell", "input", "tap", str(center_x), str(center_y)])
            log(f"已点击坐标 ({center_x}, {center_y})")
            return True
        else:
            log(f"未在屏幕上找到文字: {text}")
            return False
    except Exception as e:
        log(f"执行点击失败: {e}")
        return False

def adb_back():
    """返回上一级"""
    log("执行工具: 返回")
    subprocess.run(["adb", "shell", "input", "keyevent", "4"])
    return True

def adb_home():
    """回到主屏幕"""
    log("执行工具: 回到主页")
    subprocess.run(["adb", "shell", "input", "keyevent", "3"])
    return True

# --- AI 通信部分 ---

def query_ollama_with_tools(image_path, goal):
    url = "http://localhost:11434/api/generate"
    
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    # 在 Prompt 中定义“工具”和输出格式
    system_prompt = f"""
你是一个 Android 自动化助手。你可以根据屏幕截图选择合适的工具来完成任务。

可用的工具函数:
1. adb_click_text(text): 点击屏幕上显示的指定文字内容。
2. adb_back(): 按下返回键。
3. adb_home(): 回到主屏幕。

你的输出必须是合法的 JSON 格式，例如:
{{ "tool": "adb_click_text", "args": {{ "text": "Battery" }}, "thought": "我看到了电池选项，准备点击它" }}

当前任务目标: {goal}
"""

    payload = {
        "model": "gemma4:latest",
        "prompt": system_prompt,
        "images": [img_b64],
        "format": "json", # 强制返回 JSON
        "stream": False
    }

    log("正在询问 AI 并请求调用工具...")
    try:
        r = requests.post(url, json=payload, timeout=60)
        return r.json().get("response")
    except Exception as e:
        return str(e)

def main():
    # 确保我们在设置界面
    log("初始化：打开设置界面...")
    subprocess.run(["adb", "shell", "am", "start", "-a", "android.settings.SETTINGS"])
    time.sleep(3)

    screenshot = "tool_test_screen.png"
    subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=open(screenshot, "wb"))

    goal = "我想去看看电池（Battery）的相关设置"
    
    # 获取 AI 的决策
    response_json = query_ollama_with_tools(screenshot, goal)
    log(f"AI 响应: {response_json}")

    try:
        res = json.loads(response_json)
        tool_name = res.get("tool")
        args = res.get("args", {})
        thought = res.get("thought", "")

        print(f"\nAI 的思考过程: {thought}")
        
        if tool_name == "adb_click_text":
            adb_click_text(args.get("text"))
        elif tool_name == "adb_back":
            adb_back()
        elif tool_name == "adb_home":
            adb_home()
        else:
            log("AI 选择了未知的工具。")

    except Exception as e:
        log(f"解析 AI 响应失败: {e}")

if __name__ == "__main__":
    main()
