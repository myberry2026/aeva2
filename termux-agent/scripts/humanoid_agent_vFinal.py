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

# --- 【全家桶】人类本能工具集 ---

def adb_click(x, y):
    log(f"-> 执行：点击 ({x}, {y})")
    run_adb(["shell", "input", "tap", str(x), str(y)])

def adb_long_press(x, y, duration=1000):
    log(f"-> 执行：长按 ({x}, {y}) {duration}ms")
    run_adb(["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration)])

def adb_scroll(direction):
    if direction == "down":
        log("-> 执行：向下翻页")
        run_adb(["shell", "input", "swipe", "500", "1600", "500", "400", "300"])
    else:
        log("-> 执行：向上翻页")
        run_adb(["shell", "input", "swipe", "500", "400", "500", "1600", "300"])

def adb_type(x, y, text):
    log(f"-> 执行：清空并在 ({x}, {y}) 输入 '{text}'")
    run_adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(0.5)
    # 暴力清空：全选(Ctrl+A) + 退格
    run_adb(["shell", "input", "keyevent", "29", "--metaState", "28672"]) 
    for _ in range(40): run_adb(["shell", "input", "keyevent", "67"])
    # 输入并回车
    safe_text = text.replace(" ", "%s")
    run_adb(["shell", "input", "text", safe_text])
    run_adb(["shell", "input", "keyevent", "66"])

def adb_system(key):
    keys = {"back": "4", "home": "3", "recents": "187"}
    log(f"-> 执行：系统按键 '{key}'")
    run_adb(["shell", "input", "keyevent", keys.get(key, "4")])

# --- UI 深度清洗引擎 ---

def get_cleaned_ui_map():
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
        clickable = a.get('clickable') == 'true'
        res_id = a.get('resource-id', '').split('/')[-1]
        
        if (text or desc or clickable) and a.get('bounds'):
            b = re.findall(r'\d+', a.get('bounds'))
            if len(b) == 4:
                x1, y1, x2, y2 = map(int, b)
                if (x2-x1) < 5 or (x2-x1) > 1075: continue # 过滤极端尺寸
                elements.append({
                    "id": idx,
                    "label": text or desc or res_id or "未命名",
                    "pos": [(x1+x2)//2, (y1+y2)//2]
                })
                idx += 1
    return elements

# --- AI 决策层 ---

def agent_think(image_path, goal, elements, history):
    url = "http://100.113.214.52:1234/v1/chat/completions"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    list_str = "\n".join([f"ID {e['id']}: '{e['label']}' @ {e['pos']}" for e in elements])

    prompt = f"""
你是一个全能 Android Agent。
任务目标: {goal}

【UI 交互清单】:
{list_str}

你可以使用的动作清单:
1. {{"action": "click", "id": ID}} - 点击。
2. {{"action": "type", "id": ID, "text": "内容"}} - 输入。
3. {{"action": "scroll", "direction": "up"|"down"}} - 翻页。
4. {{"action": "system", "key": "back"|"home"|"recents"}} - 导航。
5. {{"action": "long_press", "id": ID}} - 长按。
6. {{"action": "wait"}} - 等待。
7. {{"action": "finish"}} - 任务达成。

请结合截图和清单做出决策。必须返回 JSON 格式。
"""
    payload = {"model": "google/gemma-4-e4b", "prompt": prompt, "images": [img_b64], "format": "json", "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        return json.loads(r.json().get("response")), list_str
    except: return None, list_str

def main():
    goal = "在地图搜 'hunan restaurant'，点开第一个结果，翻页看看照片，最后连按两次‘返回’退回地图首页。"
    log("=== 启动终极全能 Agent (vFinal) ===")
    
    history = []
    for i in range(15):
        log(f"\n--- 步骤 {i+1} ---")
        pic = f"final_step_{i}.png"
        run_adb(["shell", "screencap", "-p", f"/sdcard/{pic}"])
        run_adb(["pull", f"/sdcard/{pic}", "."])
        
        elements = get_cleaned_ui_map()
        decision, list_str = agent_think(pic, goal, elements, history)
        
        # 透明化展示
        print("\n" + "="*40)
        print("【CEO 审阅：清洗后的 UI 交互清单】")
        print(list_str)
        print("="*40)

        if not decision: continue
        log(f"AI 决策: {decision.get('thought', '执行中...')}")
        
        act = decision.get("action")
        try:
            if act == "click": adb_click(*elements[decision['id']]['pos'])
            elif act == "type": adb_type(*elements[decision['id']]['pos'], decision['text'])
            elif act == "scroll": adb_scroll(decision['direction'])
            elif act == "system": adb_system(decision['key'])
            elif act == "long_press": adb_long_press(*elements[decision['id']]['pos'])
            elif act == "wait": time.sleep(3)
            elif act == "finish":
                log("✅ 终极任务达成！")
                break
        except Exception as e:
            log(f"执行出错: {e}")

        history.append(act)
        time.sleep(5)

if __name__ == "__main__":
    main()
