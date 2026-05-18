import requests
import base64
import os
import json
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"
FOLDER = "logs/run_20260510_174510"
LOG_DIR = "profiling/raw_api_logs"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def summarize_structured_storyline():
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 20 张高清原图
    imgs = []
    for i in range(1, 11):
        b = os.path.join(FOLDER, f"step_{i}_before.png")
        a = os.path.join(FOLDER, f"step_{i}_after.png")
        if os.path.exists(b): imgs.append(b)
        if os.path.exists(a): imgs.append(a)
    
    user_content = []
    for p in imgs:
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image(p)}"}})
    
    prompt = """These 20 images show a chronological Android automation session. 
Analyze the sequence and provide a HIGHLY STRUCTURED report in a Markdown table.

For each step (or pair of images), identify:
| Step | APP Name | Page Description | Action Taken | Key Observation / Change |
| :--- | :--- | :--- | :--- | :--- |

After the table, provide a brief 'Logic Flow' analysis of how the task progressed from start to finish.
Be extremely precise about UI elements, labels, and status messages."""

    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 4096, 
        "temperature": 0.2,
        "extra_body": { "num_ctx": 64000 }
    }

    print(f"[*] Sending STRUCTURED request (20 images) to {MODEL}...")
    start = time.time()
    resp = requests.post(URL, json=payload, timeout=300)
    dt = time.time() - start
    
    if resp.status_code == 200:
        res_data = resp.json()
        with open(f"{LOG_DIR}/storyline_structured_response.json", "w", encoding="utf-8") as f:
            json.dump(res_data, f, indent=2, ensure_ascii=False)
        
        msg = res_data['choices'][0]['message']
        print(f"\n[*] SUCCESS! Latency: {dt:.2f}s")
        print("\n" + "="*50 + " STRUCTURED STORYLINE AUDIT " + "="*50)
        print(f"\n{msg.get('content', '')}")
        print("="*128)
    else:
        print(f"Error {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    summarize_structured_storyline()
