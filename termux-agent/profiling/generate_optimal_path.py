import requests
import base64
import os
import json
import time
import re

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"
LOG_FILE = "logs/run_20260510_174510/agent_debug.log"
FOLDER = "logs/run_20260510_174510"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_log_context():
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 提取总目标
    goal_match = re.search(r"【总目标】: (.*?)\n", content)
    goal = goal_match.group(1) if goal_match else "Unknown"
    
    # 提取每一步的 Inventory 和 Action
    steps_data = []
    # 简单切分每个 Step
    steps = re.split(r"==================== STEP \d+ \[DECISION\]", content)
    for i, s in enumerate(steps[1:11]): # 取前 10 个 Decision Step
        inv_match = re.search(r"【当前可交互清单】.*?\n(.*?)【Gap 分析要求】", s, re.DOTALL)
        inv = inv_match.group(1).strip() if inv_match else "N/A"
        
        resp_match = re.search(r"\[RESPONSE\]:\n(.*?)\n", s, re.DOTALL)
        resp = resp_match.group(1).strip() if resp_match else "N/A"
        steps_data.append(f"Step {i+1} UI Inventory:\n{inv}\nAction Taken:\n{resp}")
    
    return goal, "\n\n".join(steps_data)

def generate_optimal_path():
    goal, context = extract_log_context()
    
    # 选 20 张高清图
    imgs = []
    for i in range(1, 11):
        b = os.path.join(FOLDER, f"step_{i}_before.png")
        a = os.path.join(FOLDER, f"step_{i}_after.png")
        if os.path.exists(b): imgs.append(b)
        if os.path.exists(a): imgs.append(a)
    
    user_content = []
    for p in imgs:
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image(p)}"}})
    
    prompt = f"""You are an Automation Architect. 
I am providing 20 images of a session, along with the UI Inventory and actions recorded in the logs.

Goal: {goal}

Context from Logs:
{context}

Based on the images (visual) and logs (semantic/UI structure), please define the OPTIMAL AUTOMATION PATH:
1. What is the minimum number of steps to achieve this goal reliably?
2. Which UI selectors (IDs, Labels, or Coordinates) are the most stable for each step?
3. What are the 'best practices' learned from this session (e.g., how to handle wait times, how to trigger 'send')?
4. Provide a pseudo-code or sequence list for a high-performance automation script.

Format your output with clear headings and a 'Final Optimization Summary'."""

    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 4096, 
        "temperature": 0.2,
        "extra_body": { "num_ctx": 64000 }
    }

    print(f"[*] Generating Optimal Path from Images + Logs (60K context)...")
    start = time.time()
    resp = requests.post(URL, json=payload, timeout=300)
    
    if resp.status_code == 200:
        print(f"\n[*] SUCCESS! {time.time()-start:.2f}s")
        print("\n" + "="*50 + " OPTIMAL AUTOMATION PATH " + "="*50)
        print(resp.json()['choices'][0]['message'].get('content'))
        print("="*125)
    else:
        print(f"Error {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    generate_optimal_path()
