import subprocess
import time
import base64
import requests
import json
import os
import re
import xml.etree.ElementTree as ET

def log(msg):
    print(f"[*] {msg}")

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

# --- 终极工具箱 ---

def adb_click(x, y):
    log(f"-> 动作：点击坐标 ({x}, {y})")
    run_adb(["shell", "input", "tap", str(x), str(y)])

def adb_back():
    log("-> 动作：按返回键")
    run_adb(["shell", "input", "keyevent", "4"])

def adb_home():
    log("-> 动作：回主屏幕")
    run_adb(["shell", "input", "keyevent", "3"])

def adb_scroll_down():
    log("-> 动作：向下滚动")
    run_adb(["shell", "input", "swipe", "500", "1500", "500", "500", "300"])

def adb_open_app(pkg):
    log(f"-> 动作：强制重启应用 {pkg}")
    run_adb(["shell", "am", "force-stop", pkg])
    time.sleep(1)
    run_adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])

def adb_replace_text(x, y, text):
    log(f"-> 动作：清空并输入 '{text}'")
    run_adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(0.5)
    # 模拟全选并删除
    run_adb(["shell", "input", "keyevent", "META_CTRL_ON", "29"]) # Ctrl+A
    for _ in range(30): run_adb(["shell", "input", "keyevent", "67"]) # Backspace
    run_adb(["shell", "input", "text", text.replace(" ", "%s")])
    run_adb(["shell", "input", "keyevent", "66"])

# --- UI 数据清洗 ---

def get_ui_map():
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml_data = run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    try:
        root = ET.fromstring(xml_data)
    except:
        return []

    elements = []
    for node in root.iter('node'):
        a = node.attrib
        text, desc, res_id = a.get('text'), a.get('content-desc'), a.get('resource-id', '').split('/')[-1]
        clickable = a.get('clickable') == 'true'
        if text or desc or clickable:
            b = re.findall(r'\d+', a.get('bounds', ''))
            if len(b) == 4:
                elements.append({
                    "text": text or desc or res_id,
                    "center": [(int(b[0])+int(b[2]))//2, (int(b[1])+int(b[3]))//2],
                    "clickable": clickable
                })
    return elements

# --- 决策核心 ---

def agent_think(image_path, goal, elements, history):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = f"""
你是一个 Android 自动驾驶 Agent。
目标: {goal}

当前屏幕可见元素:
{json.dumps(elements, ensure_ascii=False)}

历史动作: {history}

指令集 (必须从中选择):
1. {{"action": "replace_text", "x": x, "y": y, "text": "hunan restaurant"}} - 如果你在搜索页且内容不对。
2. {{"action": "click", "x": x, "y": y}} - 点击目标或卡片。
3. {{"action": "back"}} - 如果你在错误页面或详情页，需要返回。
4. {{"action": "open_app"}} - 如果应用卡死或彻底迷路。
5. {{"action": "scroll_down"}} - 寻找下方结果。
6. {{"action": "finish", "result": "原因"}} - 达成目标。

请只返回 JSON。
"""
    payload = {"model": "gemma4:latest", "prompt": prompt, "images": [img_b64], "format": "json", "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        return json.loads(r.json().get("response"))
    except: return None

def main():
    goal = "搜索 'hunan restaurant'，并点击进入一家餐厅的详情页。"
    pkg = "com.google.android.apps.maps"
    history = []
    
    log("=== 启动终极版 Agent ===")
    
    for i in range(15): # 步骤上限调高
        log(f"\n--- 步骤 {i+1} ---")
        pic = f"ultimate_step_{i}.png"
        run_adb(["shell", "screencap", "-p", f"/sdcard/{pic}"])
        run_adb(["pull", f"/sdcard/{pic}", "."])
        
        elements = get_ui_map()
        decision = agent_think(pic, goal, elements, history)
        
        if not decision: continue
        log(f"AI 思考: {decision.get('thought', '分析中...')}")
        
        act = decision.get("action")
        if act == "replace_text":
            adb_replace_text(decision['x'], decision['y'], decision['text'])
        elif act == "click":
            adb_click(decision['x'], decision['y'])
        elif act == "back":
            adb_back()
        elif act == "open_app":
            adb_open_app(pkg)
        elif act == "scroll_down":
            adb_scroll_down()
        elif act == "finish":
            log(f"✅ 任务完成: {decision.get('result')}")
            break
            
        history.append(act)
        time.sleep(5)

if __name__ == "__main__":
    main()
