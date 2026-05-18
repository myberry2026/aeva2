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

def get_ui_elements():
    """获取精简后的 UI 交互清单"""
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml_data = run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    try:
        root = ET.fromstring(xml_data)
    except: return []

    elements = []
    idx = 0
    for node in root.iter('node'):
        a = node.attrib
        text = a.get('text', '')
        desc = a.get('content-desc', '')
        res_id = a.get('resource-id', '').split('/')[-1]
        clickable = a.get('clickable') == 'true'
        
        if (text or desc or clickable) and a.get('bounds'):
            b = re.findall(r'\d+', a.get('bounds'))
            if len(b) == 4:
                x1, y1, x2, y2 = map(int, b)
                if (x2-x1) < 10 or (x2-x1) > 1070: continue
                
                elements.append({
                    "index": idx,
                    "text": text or desc or res_id,
                    "center": [(x1+x2)//2, (y1+y2)//2]
                })
                idx += 1
    return elements

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

def agent_think(image_path, goal, elements):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    # 构造精简列表
    list_str = "\n".join([f"ID {e['index']}: '{e['text']}' @ {e['center']}" for e in elements])

    prompt = f"""
你是一个 Android 自动化专家。
目标: {goal}

当前 UI 元素清单:
{list_str}

请查看截图并从清单中选择一个 ID 操作。必须返回 JSON:
{{ "thought": "中文分析", "action": "click" | "finish", "target_id": ID数字 }}
"""
    payload = {"model": "gemma4:latest", "prompt": prompt, "images": [img_b64], "format": "json", "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=120)
        return json.loads(r.json().get("response")), list_str
    except: return None, list_str

def main():
    goal = "在地图里点开 'Photos'（照片）标签，看看这家店的实拍图。"
    log("=== 启动【透明洗稿版】Agent ===")
    
    for i in range(10):
        log(f"\n--- 步骤 {i+1} ---")
        pic = f"strict_step_{i}.png"
        run_adb(["shell", "screencap", "-p", f"/sdcard/{pic}"])
        run_adb(["pull", f"/sdcard/{pic}", "."])
        
        elements = get_ui_elements()
        decision, list_str = agent_think(pic, goal, elements)
        
        # 实时打印洗稿后的清单
        print("-" * 30)
        print("【CEO 审阅：清洗后的 UI 交互清单】")
        print(list_str)
        print("-" * 30)

        if not decision: continue
        log(f"AI 思考: {decision.get('thought')}")
        
        if decision.get("action") == "finish":
            log("✅ 任务完成！")
            break
            
        target_idx = decision.get("target_id")
        for e in elements:
            if e['index'] == target_idx:
                log(f"-> 匹配成功！点击 {e['text']} @ {e['center']}")
                run_adb(["shell", "input", "tap", str(e['center'][0]), str(e['center'][1])])
                break
        
        time.sleep(5)

if __name__ == "__main__":
    main()
