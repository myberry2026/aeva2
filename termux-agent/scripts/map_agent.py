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

def adb_type(text):
    log(f"-> 正在输入文字: {text}")
    safe_text = text.replace(" ", "%s")
    run_adb(["shell", "input", "text", safe_text])
    run_adb(["shell", "input", "keyevent", "66"])

def open_app(pkg):
    log(f"-> 正在启动地图...")
    run_adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])

def agent_think(image_path, goal, elements):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = f"""
你是一个 Android 操作员。请看着截图操作地图 App 达到目标: {goal}
当前元素列表: {json.dumps(elements, ensure_ascii=False)}

请只返回 JSON:
{{
  "thought": "用中文写出你现在看到了什么，打算点哪里",
  "action": "click" | "type" | "finish",
  "x": 坐标, "y": 坐标, "text": "要输入的文字"
}}
"""
    payload = {"model": "gemma4:latest", "prompt": prompt, "images": [img_b64], "format": "json", "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        return json.loads(r.json().get("response"))
    except: return None

def main():
    goal = "在 Google Maps 里搜索 'The Great Wall'"
    pkg = "com.google.android.apps.maps"
    
    # 强制回到主屏幕并启动
    run_adb(["shell", "input", "keyevent", "3"])
    time.sleep(1)
    open_app(pkg)
    time.sleep(5)

    for i in range(10):
        log(f"\n--- 步骤 {i+1} ---")
        pic = f"map_step_{i}.png"
        with open(pic, "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f)
        
        elements = get_screen_elements()
        decision = agent_think(pic, goal, elements)
        
        if not decision: break
        print(f"AI 思考: {decision['thought']}")
        
        action = decision.get("action")
        if action == "click":
            adb_click_coord(decision['x'], decision['y'])
        elif action == "type":
            adb_click_coord(decision['x'], decision['y']) # 先点一下搜索框
            time.sleep(1)
            adb_type(decision['text'])
        elif action == "finish":
            log("任务完成！")
            break
        time.sleep(4)

if __name__ == "__main__":
    main()
