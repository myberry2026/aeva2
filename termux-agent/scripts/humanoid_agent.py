import subprocess
import time
import base64
import requests
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime

def log(msg):
    print(f"[*] {msg}")

def save_debug_log(step, prompt, response):
    log_file = "agent_debug.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*20} STEP {step} {'='*20}\n")
        f.write(f"[PROMPT]:\n{prompt}\n")
        f.write(f"\n[RESPONSE]:\n{response}\n")

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

# --- 核心工具箱 ---

def adb_click(x, y):
    run_adb(["shell", "input", "tap", str(x), str(y)])

def adb_scroll(direction):
    if direction == "down": run_adb(["shell", "input", "swipe", "500", "1600", "500", "400", "300"])
    else: run_adb(["shell", "input", "swipe", "500", "400", "500", "1600", "300"])

def adb_type(x, y, text):
    run_adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(0.5)
    run_adb(["shell", "input", "keyevent", "29", "--metaState", "28672"]) # Ctrl+A
    for _ in range(40): run_adb(["shell", "input", "keyevent", "67"])
    run_adb(["shell", "input", "text", text.replace(" ", "%s")])
    run_adb(["shell", "input", "keyevent", "66"])

def adb_back(): run_adb(["shell", "input", "keyevent", "4"])
def adb_home(): run_adb(["shell", "input", "keyevent", "3"])
def adb_open_app(pkg):
    run_adb(["shell", "am", "force-stop", pkg])
    time.sleep(0.5)
    run_adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])

# --- UI 清洗与状态对比 ---

def get_ui_inventory():
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml_data = run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    try: root = ET.fromstring(xml_data)
    except: return []
    elements = []
    idx = 0
    for node in root.iter('node'):
        a = node.attrib
        text, desc, res_id = a.get('text'), a.get('content-desc'), a.get('resource-id', '').split('/')[-1]
        if (text or desc or a.get('clickable') == 'true') and a.get('bounds'):
            b = re.findall(r'\d+', a.get('bounds'))
            if len(b) == 4:
                x1, y1, x2, y2 = map(int, b)
                if (x2-x1) < 5 or (x2-x1) > 1075: continue
                elements.append({"id": idx, "label": text or desc or res_id or "Button", "pos": [(x1+x2)//2, (y1+y2)//2]})
                idx += 1
    return elements

# --- Agent 决策 ---

def agent_think(step, goal, elements, rich_history, image_path):
    url = "http://100.113.214.52:1234/v1/chat/completions"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    list_str = "\n".join([f"ID {e['id']}: '{e['label']}' @ {e['pos']}" for e in elements])
    
    # 构造有血有肉的历史回顾
    history_lines = []
    for h in rich_history[-10:]:
        line = f"Step {h['step']}: 执行了 [{h['action']}]"
        if 'target_label' in h: line += f" 目标是 '{h['target_label']}'"
        if 'status' in h: line += f" -> 结果: {h['status']}"
        history_lines.append(line)
    history_str = "\n".join(history_lines)

    prompt = f"""
你是一个具备深度记忆的 Android Agent。目标: {goal}

【当前 UI 交互清单】:
{list_str}

【历史记忆回顾】:
{history_str if history_str else "这是第一步。"}

你可以用的指令:
1. {{"action": "click", "id": ID}}
2. {{"action": "type", "id": ID, "text": "内容"}}
3. {{"action": "scroll", "direction": "up"|"down"}}
4. {{"action": "back"}}
5. {{"action": "home"}}
6. {{"action": "open_app", "pkg": "包名"}}
7. {{"action": "finish"}}

规则：
- 观察【历史记忆回顾】。如果你发现点了某个 ID 但界面没反应，那是陷阱，请换个 ID 点或者按 back。
- 只有到达最终首页才算 finish。必须返回 JSON。
"""
    payload = {"model": "google/gemma-4-e4b", "prompt": prompt, "images": [img_b64], "format": "json", "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        resp_json = r.json().get("response")
        save_debug_log(step, prompt, resp_json)
        return json.loads(resp_json), list_str
    except: return None, list_str

def main():
    goal = "在地图搜 'hunan restaurant'，点进第一个结果，看一眼照片后连续退回地图首页。"
    pkg = "com.google.android.apps.maps"
    log("=== 启动【深度记忆 3.0】Humanoid Agent ===")
    
    if os.path.exists("agent_debug.log"): os.remove("agent_debug.log")
    
    rich_history = []
    last_ui_signature = ""

    for i in range(20):
        step = i + 1
        log(f"\n--- 第 {step} 步 ---")
        pic = f"step_{i}.png"
        run_adb(["shell", "screencap", "-p", f"/sdcard/{pic}"])
        run_adb(["pull", f"/sdcard/{pic}", "."])
        
        elements = get_ui_inventory()
        current_ui_sig = str([e['label'] for e in elements]) # 简单的 UI 签名
        
        decision, list_str = agent_think(step, goal, elements, rich_history, pic)
        print(f"\n【清单】\n{list_str}\n" + "="*40)
        if not decision: continue

        # 准备记录这一步
        history_entry = {"step": step, "action": decision.get("action"), "thought": decision.get("thought", "")}
        
        act = decision.get("action")
        try:
            if act in ["click", "type", "long_press"]:
                target_el = elements[decision['id']]
                history_entry["target_label"] = target_el['label']
                if act == "click": adb_click(*target_el['pos'])
                else: adb_type(*target_el['pos'], decision['text'])
            elif act == "scroll": adb_scroll(decision['direction'])
            elif act == "back": adb_back()
            elif act == "home": adb_home()
            elif act == "open_app": adb_open_app(decision.get('pkg', pkg))
            elif act == "finish": log("✅ 达成目标！"); break
            
            # 检测 UI 是否变化
            time.sleep(4)
            new_elements = get_ui_inventory()
            new_ui_sig = str([e['label'] for e in new_elements])
            if new_ui_sig == current_ui_sig:
                history_entry["status"] = "界面未发生任何变化（点击可能无效）"
                log("⚠️ 警告：UI 未响应")
            else:
                history_entry["status"] = "成功跳转/界面已刷新"
                log("-> UI 已更新")
            
            rich_history.append(history_entry)
        except: log("执行异常")

if __name__ == "__main__":
    main()
