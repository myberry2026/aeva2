import subprocess
import time
import base64
import requests
import json
import os
import re

def log(msg):
    print(f"[*] {msg}")

# --- 核心工具 ---

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

def get_screen_elements():
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml = run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    elements = []
    # 匹配 text/content-desc 和 bounds
    matches = re.findall(r'(?:text|content-desc)="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    for m in matches:
        if m[0]: # 过滤空文字
            elements.append({
                "text": m[0],
                "center": [(int(m[1])+int(m[3]))//2, (int(m[2])+int(m[4]))//2]
            })
    return elements

def adb_click_coord(x, y):
    log(f"执行点击坐标: ({x}, {y})")
    run_adb(["shell", "input", "tap", str(x), str(y)])

def adb_type(text):
    log(f"执行输入文字: {text}")
    # 使用 adb shell input text 发送，空格转 %s
    safe_text = text.replace(" ", "%s")
    run_adb(["shell", "input", "text", safe_text])
    # 输入完按一下回车
    run_adb(["shell", "input", "keyevent", "66"])

def open_app(pkg):
    log(f"启动应用: {pkg}")
    run_adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])

# --- AI 决策层 ---

def agent_think(image_path, goal, elements, history):
    url = "http://localhost:11434/api/generate"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = f"""
你是一个 Android 自动驾驶助手。
任务目标: {goal}

当前屏幕上的可见元素及其中心坐标:
{json.dumps(elements, ensure_ascii=False)}

历史记录: {history}

请分析截图，决定下一步动作。
如果看到 'Accept & continue' 或 'No thanks' 等引导页，请优先点掉它们。
如果看到搜索框，请点击并输入搜索内容。
如果看到了搜索结果，请使用 'finish' 动作并描述你看到的内容。

请只返回 JSON 格式:
{{
  "thought": "中文思考过程",
  "action": "click" | "type" | "wait" | "finish",
  "x": 坐标, "y": 坐标, 
  "text": "要输入的内容",
  "result": "最终结果总结"
}}
"""

    payload = {
        "model": "gemma4:latest",
        "prompt": prompt,
        "images": [img_b64],
        "format": "json",
        "stream": False
    }

    try:
        r = requests.post(url, json=payload, timeout=120)
        resp_text = r.json().get("response")
        return json.loads(resp_text)
    except Exception as e:
        log(f"AI 决策解析出错: {e}")
        return None

def main():
    goal = "打开 Chrome，在搜索框输入 'today stock market' 并回车，然后告诉我你看到了哪个指数或股票的信息。"
    pkg = "com.android.chrome"
    history = []
    
    log("=== 启动 Chrome 股市搜索 Agent ===")
    open_app(pkg)
    time.sleep(5)

    for i in range(12): # 步骤多给点，因为 Chrome 引导页多
        log(f"\n--- 步骤 {i+1} ---")
        
        pic = f"chrome_step_{i}.png"
        with open(pic, "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f)
        
        elements = get_screen_elements()
        decision = agent_think(pic, goal, elements, history)
        
        if not decision: 
            log("AI 没有返回有效指令。")
            break
            
        thought = decision.get("thought", "思考中...")
        log(f"AI 思考: {thought}")
        history.append({"step": i, "action": decision.get("action")})

        action = decision.get("action")
        if action == "click":
            adb_click_coord(decision['x'], decision['y'])
        elif action == "type":
            # 先点击一下坐标确保聚焦，再输入
            adb_click_coord(decision['x'], decision['y'])
            time.sleep(1)
            adb_type(decision['text'])
        elif action == "wait":
            time.sleep(3)
        elif action == "finish":
            log(f"✅ 任务完成！AI 总结: {decision.get('result')}")
            break
        
        time.sleep(4) # 给网页加载留点时间

if __name__ == "__main__":
    main()
