import subprocess
import time
import base64
import requests
import json
import xml.etree.ElementTree as ET
import concurrent.futures

MODEL_URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL_NAME = "google/gemma-4-e4b"

def run_adb(cmd):
    start = time.time()
    res = subprocess.run(["adb"] + cmd, capture_output=True, text=True)
    return res, time.time() - start

def _take_screenshot(path):
    return run_adb(["shell", "screencap", "-p", "/sdcard/view.png"])

def _do_dump():
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml_data, t = run_adb(["shell", "cat", "/sdcard/ui.xml"])
    return xml_data.stdout, t

def call_llm(prompt, img_b64):
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
        ]}],
        "temperature": 0,
        "stream": False
    }
    start = time.time()
    resp = requests.post(MODEL_URL, json=payload).json()
    dur = time.time() - start
    
    # Try to extract thought and action
    content = resp['choices'][0]['message']['content']
    thought_len = 0
    action_str = ""
    try:
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            j = json.loads(match.group())
            thought_len = len(j.get('thought', ''))
            action_str = json.dumps({"action": j.get("action"), "id": j.get("id")})
    except:
        pass
        
    return dur, resp.get('usage', {}), thought_len, action_str

def profile_optimizations():
    print("=== PROFILING: BASELINE vs OPTIMIZED ===")
    
    # 1. Test ADB: Serial vs Concurrent
    print("\n[1] Testing System Tax: ADB Dump + Cap")
    
    # Serial
    start = time.time()
    _do_dump()
    _take_screenshot("test.png")
    serial_time = time.time() - start
    print(f"  -> Serial ADB Time: {serial_time:.2f}s")
    
    # Concurrent
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(_do_dump)
        f2 = executor.submit(_take_screenshot, "test.png")
        f1.result()
        f2.result()
    concurrent_time = time.time() - start
    print(f"  -> Concurrent ADB Time: {concurrent_time:.2f}s")
    print(f"  => POTENTIAL SAVINGS: {serial_time - concurrent_time:.2f}s")
    
    # 2. Test LLM: Long Thought vs Short Thought
    print("\n[2] Testing Generation Tax: Thought Length")
    with open("test.png", "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
        
    inventory = "ID 0: Search\nID 1: Home"
    
    # Long Thought (Baseline)
    prompt_long = f"""
    Target: Click Search. Inventory: {inventory}
    Return JSON format: {{"thought": "Please provide a very detailed and long step-by-step analysis of why you are choosing this action.", "action": "click", "id": 0}}
    """
    t_long, u_long, len_long, act_long = call_llm(prompt_long, img_b64)
    print(f"  -> Long Thought Output: {len_long} chars | Output Tokens: {u_long.get('completion_tokens', 0)}")
    print(f"  -> Total LLM Time (Long): {t_long:.2f}s")
    
    # Short Thought (Optimized)
    prompt_short = f"""
    Target: Click Search. Inventory: {inventory}
    Return JSON format: {{"thought": "Keep it under 5 words.", "action": "click", "id": 0}}
    """
    t_short, u_short, len_short, act_short = call_llm(prompt_short, img_b64)
    print(f"  -> Short Thought Output: {len_short} chars | Output Tokens: {u_short.get('completion_tokens', 0)}")
    print(f"  -> Total LLM Time (Short): {t_short:.2f}s")
    print(f"  => POTENTIAL SAVINGS: {t_long - t_short:.2f}s")

if __name__ == "__main__":
    profile_optimizations()
