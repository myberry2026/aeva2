import os
import requests
import base64
import json
import time
import re

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"
LOGS_DIR = "logs"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_session_bundle(folder_name):
    path = os.path.join(LOGS_DIR, folder_name)
    if not os.path.isdir(path): return None
    
    log_file = os.path.join(path, "agent_debug.log")
    goal = "Unknown"
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            line = f.read()
            m = re.search(r"【总目标】: (.*?)\n", line)
            if m: goal = m.group(1)

    imgs = sorted([f for f in os.listdir(path) if f.endswith(".png")])
    if not imgs: return None
    
    # 抽样 4 张代表性的图：开始、中间、关键动作、结束
    sample_indices = [0, len(imgs)//3, 2*len(imgs)//3, len(imgs)-1]
    sample_imgs = [os.path.join(path, imgs[i]) for i in sample_indices]
    
    return {"goal": goal, "images": sample_imgs}

def cross_app_masterplan():
    targets = [
        "run_20260510_163345", # NVDA Price (Browser + SMS)
        "run_20260510_160840", # YouTube Link (YouTube + SMS)
        "run_20260510_233351", # Pizza (Maps + Reasoning)
        "run_20260510_164004"  # Weather Alarm (Logic + Clock)
    ]
    
    bundles = []
    for t in targets:
        b = extract_session_bundle(t)
        if b: bundles.append(b)
    
    user_content = []
    text_context = "I am providing data from 4 DIFFERENT automation tasks to help you build a UNIVERSAL MASTERPLAN.\n\n"
    
    for i, b in enumerate(bundles):
        text_context += f"### Task {i+1} Goal: {b['goal']}\n"
        for img_p in b['images']:
            user_content.append({
                "type": "image_url", 
                "image_url": {"url": f"data:image/png;base64,{encode_image(img_p)}"}
            })
    
    prompt = f"""{text_context}

You are the Lead Architect of an AI Agent system. 
Based on these 4 diverse scenarios (Finance, Media, Location, Logic), define the 'UNIVERSAL ANDROID AUTOMATION FRAMEWORK':

1. **The Selector Hierarchy**: When should we use Resource IDs vs. Text vs. Pure Visual coordinates across different types of apps (Google vs. Third-party)?
2. **Context Persistence**: What is the best way to handle 'Cross-App Data Handover' (like copying a price or a phone number) to ensure 100% accuracy?
3. **Decision Branching**: How should the agent handle 'Conditional Logic' (like the Weather-Alarm task) to minimize redundant steps?
4. **Resilience Patterns**: Identify the top 3 'Failure Traps' seen in these logs and provide the standard 'Recovery Move' for each.

Output a high-level technical blueprint for a production-grade Agent."""

    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 4096,
        "extra_body": { "num_ctx": 64000 }
    }

    print(f"[*] Analyzing 4 Diverse Super-Tasks (16 images total)...")
    start = time.time()
    resp = requests.post(URL, json=payload, timeout=400)
    
    if resp.status_code == 200:
        print(f"\n[*] SUCCESS! {time.time()-start:.2f}s")
        print("\n" + "="*40 + " UNIVERSAL AUTOMATION MASTERPLAN " + "="*40)
        print(resp.json()['choices'][0]['message'].get('content'))
        print("="*113)
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    cross_app_masterplan()
