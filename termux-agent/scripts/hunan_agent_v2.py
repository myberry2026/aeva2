import subprocess
import time
import base64
import requests
import json
import os
import re

def log(msg):
    print(f"[*] {msg}")

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

def get_screen_elements():
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml = run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    elements = []
    matches = re.findall(r'(?:text|content-desc|resource-id)="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    for m in matches:
        if m[0]:
            elements.append({
                "text": m[0],
                "center": [(int(m[1])+int(m[3]))//2, (int(m[2])+int(m[4]))//2]
            })
    return elements

def adb_click_coord(x, y):
    log(f"-> 正在点击坐标: ({x}, {y})")
    run_adb(["shell", "input", "tap", str(x), str(y)])

def adb_clear_and_type(x, y, text):
    log(f"-> 正在清空并输入: {text}")
    # 1. 点击搜索框聚焦
    run_adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(0.5)
    # 2. 连续发送退格键清空（暴力但有效）
    for _ in range(40):
        run_adb(["shell", "input", "keyevent", "67"])
    # 3. 输入新文字
    safe_text = text.replace(" ", "%s")
    run_adb(["shell", "input", "text", safe_text])
    time.sleep(1)
    # 4. 回车搜索
    run_adb(["shell", "input", "keyevent", "66"])

def agent_think(image_path, goal, elements, history):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = f"""
你是一个 Android 操作专家。
目标: {goal}

当前元素列表: {json.dumps(elements, ensure_ascii=False)}
历史动作: {history}

指令集:
1. 如果搜索框里有旧文字（如 'The Great Wall'），请使用 'clear_and_type' 动作，目标文字是 'hunan restaurant'。
2. 如果看到搜索结果（餐厅列表），请点击其中一个。
3. 如果已进入详情页，使用 'finish'。

请返回 JSON:
{{
  "thought": "你的中文分析：是否需要清空？下一步点哪？",
  "action": "clear_and_type" | "click" | "finish",
  "x": 坐标, "y": 坐标, "text": "hunan restaurant"
}}
"""
    payload = {"model": "gemma4:latest", "prompt": prompt, "images": [img_b64], "format": "json", "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        return json.loads(r.json().get("response"))
    except: return None

def main():
    goal = "搜索 'hunan restaurant'，并点击进入其中一家湘菜馆。"
    pkg = "com.google.android.apps.maps"
    history = []
    
    log("=== 启动【聪明版】湘菜馆 Agent ===")
    run_adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])
    time.sleep(5)

    for i in range(10):
        log(f"\n--- 步骤 {i+1} ---")
        pic = f"hunan_v2_step_{i}.png"
        with open(pic, "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f)
        
        elements = get_screen_elements()
        decision = agent_think(pic, goal, elements, history)
        
        if not decision: continue
        print(f"AI 思考: {decision.get('thought', '...')}")
        
        action = decision.get("action")
        if action == "clear_and_type":
            adb_clear_and_type(decision['x'], decision['y'], decision['text'])
        elif action == "click":
            adb_click_coord(decision['x'], decision['y'])
        elif action == "finish":
            log("✅ 任务完成！")
            break
        
        history.append(action)
        time.sleep(5)

if __name__ == "__main__":
    main()
