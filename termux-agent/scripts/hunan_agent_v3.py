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

def get_screen_data():
    """获取屏幕截图和所有UI元素"""
    pic = "current_screen.png"
    with open(pic, "wb") as f:
        subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f)
    
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml = run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    
    elements = []
    # 提取 text, content-desc 和精确的 bounds
    pattern = r'(?:text|content-desc)="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
    for m in re.finditer(pattern, xml):
        text, x1, y1, x2, y2 = m.groups()
        elements.append({
            "text": text,
            "bounds": [int(x1), int(y1), int(x2), int(y2)],
            "center": [(int(x1)+int(x2))//2, (int(y1)+int(y2))//2]
        })
    return pic, elements

def adb_smart_click(x, y):
    log(f"-> 正在执行精确点击: ({x}, {y})")
    run_adb(["shell", "input", "tap", str(x), str(y)])

def adb_force_replace_text(x, y, text):
    log(f"-> 正在强制替换文字为: {text}")
    run_adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(0.5)
    # 全选并删除 (Ctrl+A, Backspace)
    run_adb(["shell", "input", "keyevent", "29", "--metaState", "28672"]) # Ctrl+A
    run_adb(["shell", "input", "keyevent", "67"]) # Delete
    # 再次删除以防万一
    for _ in range(20): run_adb(["shell", "input", "keyevent", "67"])
    
    # 输入新文字并回车
    safe_text = text.replace(" ", "%s")
    run_adb(["shell", "input", "text", safe_text])
    run_adb(["shell", "input", "keyevent", "66"])

def agent_think(image_path, goal, elements, history):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = f"""
你是一个 Android 自动驾驶专家。
目标: {goal}

当前屏幕可见元素(含坐标):
{json.dumps(elements, ensure_ascii=False)}

历史记录: {history}

指令:
1. 观察截图。如果搜索框内容不对，请使用 'replace_text'。
2. 如果看到搜索结果，请点击卡片的中心坐标。
3. 如果任务完成，请使用 'finish'。

返回 JSON:
{{
  "thought": "你的中文分析",
  "action": "replace_text" | "click" | "finish",
  "x": 坐标, "y": 坐标, "text": "hunan restaurant"
}}
"""
    payload = {"model": "gemma4:latest", "prompt": prompt, "images": [img_b64], "format": "json", "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        return json.loads(r.json().get("response"))
    except: return None

def main():
    goal = "在地图搜索 'hunan restaurant'，并成功点击进入一家餐厅的详情页。"
    history = []
    
    log("=== 启动【Agent 3.0】精确实战版 ===")
    # 确保 Chrome/Maps 在前台
    run_adb(["shell", "monkey", "-p", "com.google.android.apps.maps", "1"])
    time.sleep(5)

    for i in range(10):
        log(f"\n--- 步骤 {i+1} ---")
        pic, elements = get_screen_data()
        
        # 调试：把当前图保存一下
        os.system(f"cp {pic} debug_step_{i}.png")
        
        decision = agent_think(pic, goal, elements, history)
        if not decision: continue
        
        log(f"AI 思考: {decision.get('thought')}")
        
        action = decision.get("action")
        if action == "replace_text":
            adb_force_replace_text(decision['x'], decision['y'], decision['text'])
        elif action == "click":
            adb_smart_click(decision['x'], decision['y'])
        elif action == "finish":
            log("✅ 成功进入详情页，任务达成！")
            break
        
        history.append(action)
        time.sleep(5)

if __name__ == "__main__":
    main()
