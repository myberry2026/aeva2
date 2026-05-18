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

def get_cleaned_elements():
    """清洗 XML，只保留可交互或有意义的元素"""
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml_data = run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    
    try:
        root = ET.fromstring(xml_data)
    except:
        return []

    interactive_elements = []
    
    for node in root.iter('node'):
        attrib = node.attrib
        text = attrib.get('text', '')
        desc = attrib.get('content-desc', '')
        res_id = attrib.get('resource-id', '').split('/')[-1] # 只拿最后的 ID 名
        clickable = attrib.get('clickable', 'false') == 'true'
        focusable = attrib.get('focusable', 'false') == 'true'
        bounds = attrib.get('bounds', '')

        # 只要带文字的，或者能点/能聚焦的
        if text or desc or clickable or focusable:
            # 解析坐标 [x1,y1][x2,y2]
            b = re.findall(r'\d+', bounds)
            if len(b) == 4:
                x1, y1, x2, y2 = map(int, b)
                center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
                
                # 过滤掉全屏容器（通常是背景）
                if (x2 - x1) > 1000 and (y2 - y1) > 2000:
                    continue
                    
                interactive_elements.append({
                    "type": attrib.get('class', '').split('.')[-1],
                    "text": text,
                    "desc": desc,
                    "id": res_id,
                    "center": [center_x, center_y],
                    "interactable": clickable or focusable
                })

    # 去重：如果同一个位置有多个描述，合并它们
    unique_elements = {}
    for el in interactive_elements:
        pos = tuple(el['center'])
        if pos not in unique_elements:
            unique_elements[pos] = el
        else:
            # 补全信息
            if not unique_elements[pos]['text']: unique_elements[pos]['text'] = el['text']
            if not unique_elements[pos]['desc']: unique_elements[pos]['desc'] = el['desc']
            
    return list(unique_elements.values())

def adb_click(x, y):
    log(f"-> 动作：点击 ({x}, {y})")
    run_adb(["shell", "input", "tap", str(x), str(y)])

def adb_replace_text(x, y, text):
    log(f"-> 动作：清空并输入 '{text}'")
    run_adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(0.5)
    # 暴力清空：全选 + 删除
    run_adb(["shell", "input", "keyevent", "META_CTRL_ON", "29"]) # Ctrl+A (某些版本adb)
    run_adb(["shell", "input", "keyevent", "67"] * 30) # 连按退格
    run_adb(["shell", "input", "text", text.replace(" ", "%s")])
    run_adb(["shell", "input", "keyevent", "66"])

def agent_think(image_path, goal, elements):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    # 将清洗后的元素格式化为精简字符串，节省 Token
    elements_str = ""
    for i, el in enumerate(elements):
        elements_str += f"[{i}] {el['type']} | '{el['text'] or el['desc'] or el['id']}' | Pos: {el['center']}\n"

    prompt = f"""
你是一个 Android 自动化 Agent。
目标: {goal}

当前屏幕截图中的关键可交互元素:
{elements_str}

请结合截图和以上列表，决定下一步。
如果是搜索，请确保清空旧文字。
如果是选择餐厅，请点击对应的坐标。

请只返回 JSON:
{{
  "thought": "中文分析",
  "action": "click" | "type" | "finish",
  "x": 坐标, "y": 坐标, "text": "hunan restaurant"
}}
"""
    payload = {"model": "gemma4:latest", "prompt": prompt, "images": [img_b64], "format": "json", "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        return json.loads(r.json().get("response"))
    except: return None

def main():
    goal = "在 Google Maps 搜索 'hunan restaurant'，并点击进入第一个搜索结果的详情页。"
    log("=== 启动【深度清洗版】Agent Pro ===")
    
    # 初始化
    run_adb(["shell", "monkey", "-p", "com.google.android.apps.maps", "1"])
    time.sleep(5)

    for i in range(10):
        log(f"\n--- 步骤 {i+1} ---")
        # 1. 截图
        pic = f"pro_step_{i}.png"
        run_adb(["shell", "screencap", "-p", f"/sdcard/{pic}"])
        run_adb(["pull", f"/sdcard/{pic}", "."])
        
        # 2. 洗稿 XML
        elements = get_cleaned_elements()
        
        # 3. AI 决策
        decision = agent_think(pic, goal, elements)
        if not decision: continue
        
        log(f"AI 思考: {decision.get('thought')}")
        
        # 4. 执行
        action = decision.get("action")
        if action == "type":
            adb_replace_text(decision['x'], decision['y'], decision['text'])
        elif action == "click":
            adb_click(decision['x'], decision['y'])
        elif action == "finish":
            log("✅ 成功达成目标！")
            break
        
        time.sleep(5)

if __name__ == "__main__":
    main()
