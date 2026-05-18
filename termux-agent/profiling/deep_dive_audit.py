import os
import requests
import base64
import json
import time
import re
import sys

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"
LOGS_DIR = "logs"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def deep_audit(folder_name):
    path = os.path.join(LOGS_DIR, folder_name)
    if not os.path.isdir(path): 
        print(f"Error: Folder {path} not found.")
        return
    
    # 1. 提取总目标
    log_file = os.path.join(path, "agent_debug.log")
    goal = "Unknown"
    log_content = ""
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            log_content = f.read()
            m = re.search(r"【总目标】: (.*?)\n", log_content)
            if m: goal = m.group(1)

    # 2. 收集所有图片 (按步数排序)
    imgs = sorted([f for f in os.listdir(path) if f.endswith(".png")])
    img_paths = [os.path.join(path, f) for f in imgs]
    
    # 3. 收集所有相关的 XML/Inventory 记录 (从 log 里提取)
    # 我们直接把 log 里的决策过程分段
    steps = re.split(r"==================== STEP \d+ \[DECISION\]", log_content)
    context_text = f"### DETAILED AUDIT FOR SESSION: {folder_name}\n"
    context_text += f"### GOAL: {goal}\n\n"
    
    for i, s in enumerate(steps[1:]): # 跳过第一段开场白
        # 提取当前步的 Inventory 和 Action
        inv_match = re.search(r"【当前可交互清单】.*?\n(.*?)【Gap 分析要求】", s, re.DOTALL)
        inv = inv_match.group(1).strip() if inv_match else "N/A"
        
        resp_match = re.search(r"\[RESPONSE\]:\n(.*?)\n", s, re.DOTALL)
        resp = resp_match.group(1).strip() if resp_match else "N/A"
        
        context_text += f"--- STEP {i+1} ---\n"
        context_text += f"UI INVENTORY:\n{inv}\n"
        context_text += f"AGENT ACTION & THOUGHT:\n{resp}\n\n"

    # 4. 构建 Payload
    user_content = []
    # 喂前 20 张图 (防止 OOM)
    for p in img_paths[:20]:
        user_content.append({
            "type": "image_url", 
            "image_url": {"url": f"data:image/png;base64,{encode_image(p)}"}})
    
    prompt = f"""{context_text}

You are performing a DEEP DIVE AUDIT of this specific session.
Analyze the sequence of images and logs above to define the PERFECT EXECUTION PATH for this task.

Please identify:
1. **Inefficiencies**: Where did the agent hesitate or take redundant steps?
2. **Selector Optimization**: Which Resource IDs or Text labels were the most reliable for YouTube navigation and SMS sharing?
3. **The 'Golden Path'**: Provide a step-by-step sequence of actions (Pseudo-code) that achieves the goal with ZERO errors and maximum speed.
4. **Resilience**: If the 'Share' menu or 'Copy link' button doesn't appear immediately, what is the best waiting/retry strategy?

Output a comprehensive 'Optimal Path Blueprint' for this specific task."""

    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 4096,
        "extra_body": { "num_ctx": 64000 }
    }

    print(f"[*] Auditing {folder_name}: {goal}")
    print(f"[*] Ingesting {len(img_paths[:20])} images and full step-by-step logs...")
    
    start = time.time()
    resp = requests.post(URL, json=payload, timeout=600)
    
    if resp.status_code == 200:
        output_file = f"profiling/audit_{folder_name}.md"
        content = resp.json()['choices'][0]['message'].get('content')
        with open(output_file, "w") as f:
            f.write(content)
        print(f"\n[*] SUCCESS! {time.time()-start:.2f}s")
        print(f"[*] Audit Report saved to: {output_file}")
        print("\n" + "="*40 + " OPTIMAL PATH BLUEPRINT " + "="*40)
        print(content[:2000] + "..." if len(content) > 2000 else content)
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        deep_audit(sys.argv[1])
    else:
        # 默认跑那个 YouTube 复杂的
        deep_audit("run_20260510_160840")
