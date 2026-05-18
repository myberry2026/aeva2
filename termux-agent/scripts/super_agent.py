import subprocess
import time
import base64
import requests
import json
import os
import re

def log(msg):
    print(f"[*] {msg}")

# --- 核心工具 ---

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

def get_screen_elements():
    """获取当前屏幕上所有带文字的元素及其坐标"""
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml = run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    elements = []
    # 匹配 text 和 bounds
    matches = re.findall(r'text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    for m in matches:
        elements.append({
            "text": m[0],
            "center": [(int(m[1])+int(m[3]))//2, (int(m[2])+int(m[4]))//2]
        })
    return elements

def adb_click_coord(x, y):
    log(f"执行点击坐标: ({x}, {y})")
    run_adb(["shell", "input", "tap", str(x), str(y)])

def adb_type(text):
    log(f"执行输入文字: {text}")
    # 简单处理空格
    safe_text = text.replace(" ", "%s")
    run_adb(["shell", "input", "text", safe_text])

def open_app(pkg):
    log(f"启动应用: {pkg}")
    run_adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])

# --- AI 决策层 ---

def agent_think(image_path, goal, elements, history):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = f"""
你是一个 Android 高级操作助手。
任务目标: {goal}

当前屏幕上的可见文字元素及其中心坐标:
{json.dumps(elements, ensure_ascii=False)}

历史动作: {history}

请分析截图和元素列表，决定下一步动作。
你可以选择以下动作之一:
1. {{"action": "click", "x": 100, "y": 200, "reason": "为什么要点这里"}}
2. {{"action": "type", "text": "内容", "reason": "为什么要输入"}}
3. {{"action": "wait", "seconds": 2}}
4. {{"action": "finish", "result": "结果说明"}}

请务必只返回 JSON 格式。
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
        log(f"AI 决策出错: {e}")
        return None

def main():
    goal = "打开时钟应用 (Clock)，点击 'Alarm' 标签，并尝试点击添加闹钟按钮 (+)。"
    pkg = "com.google.android.deskclock"
    history = []
    
    log("=== 启动高级 Agent ===")
    open_app(pkg)
    time.sleep(4)

    for i in range(8):
        log(f"\n--- 步骤 {i+1} ---")
        
        # 1. 采集数据
        pic = f"agent_v2_step_{i}.png"
        with open(pic, "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f)
        
        elements = get_screen_elements()
        
        # 2. AI 决策
        decision = agent_think(pic, goal, elements, history)
        if not decision: break
        
        log(f"AI 决策: {decision['reason']}")
        history.append(decision)

        # 3. 执行动作
        action = decision.get("action")
        if action == "click":
            adb_click_coord(decision['x'], decision['y'])
        elif action == "type":
            adb_type(decision['text'])
        elif action == "wait":
            time.sleep(decision['seconds'])
        elif action == "finish":
            log(f"✅ 任务完成: {decision['result']}")
            break
        
        time.sleep(3)

if __name__ == "__main__":
    main()
