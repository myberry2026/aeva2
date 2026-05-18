import subprocess
import time
import base64
import requests
import json
import re

def log(msg):
    print(f"[*] {msg}")

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

def ad_click_text(text):
    log(f"正在尝试点击按钮: {text}")
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml = run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    # 匹配坐标
    match = re.search(f'text="{text}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml, re.IGNORECASE)
    if not match:
        # 针对计算器，有时text在content-desc里
        match = re.search(f'content-desc="{text}"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml, re.IGNORECASE)
    
    if match:
        x1, y1, x2, y2 = map(int, match.groups())
        run_adb(["shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2)])
        return True
    return False

def query_ai(image_path, task_desc):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = f"""
你是一个手机操作助手。
当前任务: {task_desc}

请查看截图，并告诉我下一步该点击哪个按钮。
如果是点击数字或符号，直接给出按钮上的字符。
如果你认为任务已完成并看到了结果，请告诉我结果。

请按照以下格式返回 JSON:
{{
  "thought": "你的中文思考过程，解释为什么要这么做",
  "action": "click",
  "target": "按钮上的文字（例如 '1' 或 '+' 或 '='）",
  "finished": false,
  "result": ""
}}
"""
    payload = {
        "model": "gemma4:latest",
        "prompt": prompt,
        "images": [img_b64],
        "format": "json",
        "stream": False
    }
    r = requests.post(url, json=payload, timeout=90)
    return json.loads(r.json().get("response"))

def main():
    task = "打开计算器，计算 12 + 34 等于多少。"
    log(f"开始任务: {task}")
    
    # 1. 强制回到主屏幕并打开计算器
    run_adb(["shell", "input", "keyevent", "3"])
    time.sleep(1)
    run_adb(["shell", "monkey", "-p", "com.android.calculator2", "1"])
    time.sleep(2)

    for i in range(10): # 最多操作10步
        # 截图
        pic = f"calc_step_{i}.png"
        with open(pic, "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f)
        
        # 问 AI
        res = query_ai(pic, task)
        print(f"\n--- 步骤 {i+1} ---")
        print(f"AI 思考: {res['thought']}")
        
        if res.get('finished'):
            print(f"✅ 任务完成！最终结果是: {res['result']}")
            break
        
        target = res['target']
        if not ad_click_text(target):
            log(f"哎呀，屏幕上没找着按钮 '{target}'，我试着直接点坐标或按键...")
            # 如果是数字，直接发按键码作为兜底
            if target.isdigit():
                run_adb(["shell", "input", "keyevent", str(int(target) + 7)])
            elif target == "+": run_adb(["shell", "input", "keyevent", "81"])
            elif target == "=": run_adb(["shell", "input", "keyevent", "66"])
        
        time.sleep(2)

if __name__ == "__main__":
    main()
