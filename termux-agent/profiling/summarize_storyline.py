import requests
import base64
import os
import json
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"
LOG_DIR = "profiling/raw_api_logs"
FOLDER = "logs/run_20260510_174510"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def summarize_storyline():
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 选 14 张图 (Step 1-7 的 before/after)
    imgs = []
    for i in range(1, 8):
        b = os.path.join(FOLDER, f"step_{i}_before.png")
        a = os.path.join(FOLDER, f"step_{i}_after.png")
        if os.path.exists(b): imgs.append(b)
        if os.path.exists(a): imgs.append(a)
    
    print(f"[*] Preparing {len(imgs)} images for storyline analysis...")

    user_content = []
    for p in imgs:
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image(p)}"}})
    
    prompt = """These 20 images are a chronological sequence of an Android automation experiment. 
Please summarize the 'Storyline' of this session:
1. What was the starting point and goal?
2. What specific actions were taken across the steps?
3. What was the final outcome or state?
Provide a cohesive narrative of the events."""

    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 2048,
        "temperature": 0.2
    }

    # 保存请求包
    with open(f"{LOG_DIR}/storyline_request.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    print(f"[*] Sending storyline request (14 images) to {MODEL}...")
    start = time.time()
    resp = requests.post(URL, json=payload, timeout=300)
    dt = time.time() - start
    
    # 保存返回包
    if resp.status_code == 200:
        res_data = resp.json()
        with open(f"{LOG_DIR}/storyline_response.json", "w", encoding="utf-8") as f:
            json.dump(res_data, f, indent=2, ensure_ascii=False)
        
        msg = res_data['choices'][0]['message']
        content = msg.get('content', '')
        thinking = msg.get('reasoning_content', '')
        
        print(f"\n[*] SUCCESS! Latency: {dt:.2f}s")
        print("\n" + "="*50 + " STORYLINE SUMMARY " + "="*50)
        print(f"\n[THINKING]\n{thinking}")
        print(f"\n[REPLY]\n{content}")
        print("="*119)
    else:
        print(f"Error {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    summarize_storyline()
