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
    # 扩大匹配范围，包括内容描述（content-desc）
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

def adb_type_chinese(text):
    log(f"-> 正在输入文字: {text}")
    # 中文在ADB输入中比较麻烦，我们通过 clipboard 或者输入法模拟
    # 这里我们先尝试直接输入（部分模拟器支持），如果不行再用广播
    run_adb(["shell", "input", "text", text]) 
    time.sleep(1)
    run_adb(["shell", "input", "keyevent", "66"]) # 回车搜索

def agent_think(image_path, goal, elements, history):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = f"""
你是一个专业的 Android 地图操作员。
目标: {goal}

当前元素列表: {json.dumps(elements, ensure_ascii=False)}
历史记录: {history}

指令集:
1. 如果还没搜索，请点击搜索框并输入 '湘菜馆'。
2. 如果已经看到搜索结果（如餐厅名称、地址、评分），请点击其中一个餐厅卡片的正中心。
3. 如果任务已完成（已经点进了餐厅详情页），请使用 'finish'。

请只返回 JSON:
{{
  "thought": "用中文描述你看到了什么，为什么要点这里",
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
    goal = "搜索附近的 '湘菜馆'，并点击进入其中一家的详情页面。"
    pkg = "com.google.android.apps.maps"
    history = []
    
    log("=== 启动【湘菜馆】探索 Agent ===")
    run_adb(["shell", "input", "keyevent", "3"])
    time.sleep(1)
    run_adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])
    time.sleep(6)

    for i in range(12):
        log(f"\n--- 步骤 {i+1} ---")
        pic = f"hunan_step_{i}.png"
        with open(pic, "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f)
        
        elements = get_screen_elements()
        decision = agent_think(pic, goal, elements, history)
        
        if not decision: 
            log("AI 响应超时或出错。")
            continue
            
        print(f"AI 思考: {decision.get('thought', '...')}")
        history.append(decision.get("action"))
        
        action = decision.get("action")
        if action == "click":
            adb_click_coord(decision['x'], decision['y'])
        elif action == "type":
            adb_click_coord(decision['x'], decision['y'])
            time.sleep(1)
            # 针对模拟器，我们将 '湘菜馆' 拆开输入或直接输入
            adb_type_chinese("hunan%srestaurant") # 模拟器对中文输入支持有限，用英文关键词搜也能找到湘菜馆
        elif action == "finish":
            log("✅ 任务完成！AI 已经帮你找到了好吃的湘菜馆。")
            break
        time.sleep(5)

if __name__ == "__main__":
    main()
