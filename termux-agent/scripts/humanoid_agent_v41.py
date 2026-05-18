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

# --- 核心动作集 ---

def adb_click(x, y):
    log(f"-> 动作：点击 ({x}, {y})")
    run_adb(["shell", "input", "tap", str(x), str(y)])

def adb_scroll(direction):
    log(f"-> 动作：{direction} 翻页")
    if direction == "down": run_adb(["shell", "input", "swipe", "500", "1500", "500", "500", "300"])
    else: run_adb(["shell", "input", "swipe", "500", "500", "500", "1500", "300"])

def adb_type(x, y, text):
    log(f"-> 动作：在 ({x}, {y}) 强制输入 '{text}'")
    run_adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(0.5)
    # 全选删除
    run_adb(["shell", "input", "keyevent", "29", "--metaState", "28672"]) 
    run_adb(["shell", "input", "keyevent", "67"])
    run_adb(["shell", "input", "text", text.replace(" ", "%s")])
    run_adb(["shell", "input", "keyevent", "66"])

def adb_back():
    log("-> 动作：按 [返回键] (遇到卡顿或错误页面必用)")
    run_adb(["shell", "input", "keyevent", "4"])

# --- UI 清洗 ---

def get_ui_map():
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml_data = run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    try:
        root = ET.fromstring(xml_data)
    except: return []

    elements = []
    idx = 0
    for node in root.iter('node'):
        a = node.attrib
        text, desc = a.get('text', ''), a.get('content-desc', '')
        if (text or desc or a.get('clickable') == 'true') and a.get('bounds'):
            b = re.findall(r'\d+', a.get('bounds'))
            if len(b) == 4:
                x1, y1, x2, y2 = map(int, b)
                if (x2-x1) < 10 or (x2-x1) > 1070: continue
                elements.append({"id": idx, "label": text or desc or "Button", "pos": [(x1+x2)//2, (y1+y2)//2]})
                idx += 1
    return elements

# --- Agent 决策 ---

def agent_think(image_path, goal, elements, history):
    url = "http://100.113.214.52:1234/v1/chat/completions"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    list_str = "\n".join([f"ID {e['id']}: '{e['label']}' @ {e['pos']}" for e in elements])

    prompt = f"""
你是一个 Android 高级操作员。
目标: {goal}

【当前可交互列表】:
{list_str}

【历史动作】: {history[-5:]}

注意：
1. 如果你发现自己在同一个页面重复操作（比如反复输入同一个词），说明当前路径错了，请【务必】使用 'back' 动作退回上一级。
2. 只有看到明确的餐厅信息或详情，才算搜索成功。

返回 JSON:
{{ "thought": "中文分析：我刚才是不是迷路了？如果是，我该按返回键吗？", "action": "click"|"type"|"scroll"|"back"|"finish", "id": ID, "text": "内容" }}
"""
    payload = {"model": "google/gemma-4-e4b", "prompt": prompt, "images": [img_b64], "format": "json", "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        return json.loads(r.json().get("response")), list_str
    except: return None, list_str

def main():
    goal = "搜索湘菜馆并看一眼照片，完成后按返回键退回地图主页。"
    log("=== 启动【防死循环版】Agent v4.1 ===")
    
    history = []
    for i in range(12):
        log(f"\n--- 步骤 {i+1} ---")
        pic = f"v41_step_{i}.png"
        run_adb(["shell", "screencap", "-p", f"/sdcard/{pic}"])
        run_adb(["pull", f"/sdcard/{pic}", "."])
        
        elements = get_ui_map()
        decision, list_str = agent_think(pic, goal, elements, history)
        
        if not decision: continue
        log(f"AI 思考: {decision.get('thought')}")
        
        act = decision.get("action")
        if act == "back": adb_back()
        elif act == "type": adb_type(*elements[decision['id']]['pos'], decision['text'])
        elif act == "click": adb_click(*elements[decision['id']]['pos'])
        elif act == "scroll": adb_scroll("down")
        elif act == "finish":
            log("✅ 目标达成！")
            break
        
        history.append(act)
        time.sleep(5)

if __name__ == "__main__":
    main()
