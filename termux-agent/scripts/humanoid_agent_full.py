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

# --- 【全功能】人类本能工具集（绝不删减版） ---

def adb_click(x, y):
    log(f"-> 动作：点击坐标 ({x}, {y})")
    run_adb(["shell", "input", "tap", str(x), str(y)])

def adb_long_press(x, y, duration=1000):
    log(f"-> 动作：长按坐标 ({x}, {y}) {duration}ms")
    run_adb(["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration)])

def adb_scroll(direction):
    log(f"-> 动作：向{direction}翻页")
    if direction == "down":
        run_adb(["shell", "input", "swipe", "500", "1600", "500", "400", "300"])
    else:
        run_adb(["shell", "input", "swipe", "500", "400", "500", "1600", "300"])

def adb_type(x, y, text):
    log(f"-> 动作：在 ({x}, {y}) 清空并输入 '{text}'")
    run_adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(0.5)
    # 强力清空：全选(Ctrl+A) + 退格(Backspace)
    run_adb(["shell", "input", "keyevent", "29", "--metaState", "28672"]) 
    for _ in range(40): run_adb(["shell", "input", "keyevent", "67"])
    # 输入新内容
    safe_text = text.replace(" ", "%s")
    run_adb(["shell", "input", "text", safe_text])
    run_adb(["shell", "input", "keyevent", "66"]) # 回车

def adb_system(key):
    keys = {"back": "4", "home": "3", "recents": "187"}
    log(f"-> 动作：系统导航按键 '{key}'")
    run_adb(["shell", "input", "keyevent", keys.get(key, "4")])

def adb_wait(seconds):
    log(f"-> 动作：静止等待 {seconds} 秒")
    time.sleep(seconds)

# --- UI 深度清洗 ---

def get_ui_inventory():
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
                if (x2-x1) < 5 or (x2-x1) > 1075: continue
                elements.append({
                    "id": idx,
                    "label": text or desc or res_id or "Button",
                    "pos": [(x1+x2)//2, (y1+y2)//2]
                })
                idx += 1
    return elements

# --- Agent 决策核心 ---

def agent_think(image_path, goal, elements, history):
    url = "http://100.113.214.52:1234/v1/chat/completions"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    list_str = "\n".join([f"ID {e['id']}: '{e['label']}' @ {e['pos']}" for e in elements])

    prompt = f"""
你是一个具备完整人类本能的 Android Agent。
目标: {goal}

【UI 交互清单】:
{list_str}

【历史记录】: {history[-5:]}

你可以执行的动作:
1. {{"action": "click", "id": ID}} - 点击
2. {{"action": "type", "id": ID, "text": "内容"}} - 输入
3. {{"action": "scroll", "direction": "up"|"down"}} - 翻页
4. {{"action": "system", "key": "back"|"home"|"recents"}} - 系统键
5. {{"action": "long_press", "id": ID}} - 长按
6. {{"action": "wait", "seconds": 3}} - 等待
7. {{"action": "finish"}} - 完成

规则：
- 如果你发现自己在同一个地方打转，立即使用 'system', 'key': 'back'。
- 请务必返回合法的 JSON 格式。
"""
    payload = {"model": "google/gemma-4-e4b", "prompt": prompt, "images": [img_b64], "format": "json", "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        return json.loads(r.json().get("response")), list_str
    except: return None, list_str

def main():
    goal = "在地图搜 'hunan restaurant'，点开第一个结果，看看照片，最后按 'back' 返回地图主页。"
    log("=== 启动【全功能】Agent Pro (Humanoid) ===")
    
    # 预检：确保特效开启
    run_adb(["shell", "settings", "put", "system", "show_touches", "1"])
    run_adb(["shell", "settings", "put", "system", "pointer_location", "0"]) # 关掉丑线
    
    history = []
    for i in range(15):
        log(f"\n--- 步骤 {i+1} ---")
        pic = f"full_step_{i}.png"
        run_adb(["shell", "screencap", "-p", f"/sdcard/{pic}"])
        run_adb(["pull", f"/sdcard/{pic}", "."])
        
        elements = get_ui_inventory()
        decision, list_str = agent_think(pic, goal, elements, history)
        
        print("\n" + "="*50)
        print("【CEO 审阅：当前 UI 交互清单】")
        print(list_str)
        print("="*50)

        if not decision: continue
        log(f"AI 思考: {decision.get('thought', '决策中...')}")
        
        act = decision.get("action")
        try:
            if act == "click": adb_click(*elements[decision['id']]['pos'])
            elif act == "type": adb_type(*elements[decision['id']]['pos'], decision['text'])
            elif act == "scroll": adb_scroll(decision['direction'])
            elif act == "system": adb_system(decision['key'])
            elif act == "long_press": adb_long_press(*elements[decision['id']]['pos'])
            elif act == "wait": adb_wait(decision.get('seconds', 3))
            elif act == "finish":
                log("✅ 终极任务达成！")
                break
        except Exception as e:
            log(f"执行操作出错: {e}")

        history.append(act)
        time.sleep(5)

if __name__ == "__main__":
    main()
