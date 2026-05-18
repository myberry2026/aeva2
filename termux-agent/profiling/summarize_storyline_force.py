import requests
import base64
import os
import json
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"
FOLDER = "logs/run_20260510_174510"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def summarize_storyline_force():
    # 重回 20 张图
    imgs = []
    for i in range(1, 11):
        b = os.path.join(FOLDER, f"step_{i}_before.png")
        a = os.path.join(FOLDER, f"step_{i}_after.png")
        if os.path.exists(b): imgs.append(b)
        if os.path.exists(a): imgs.append(a)
    
    user_content = []
    for p in imgs:
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image(p)}"}})
    
    user_content.append({"type": "text", "text": "Describe the storyline of these 20 images."})

    # 尝试所有可能的扩容参数
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 4096, 
        "temperature": 0.2,
        "extra_body": {
            "num_ctx": 32768,
            "context_length": 32768,
            "max_model_len": 32768,
            "gpu_memory_utilization": 0.9
        }
    }

    print(f"[*] Sending storyline request (20 images) with FORCE parameters...")
    resp = requests.post(URL, json=payload, timeout=300)
    
    if resp.status_code == 200:
        print(f"[*] SUCCESS!")
        print(resp.json()['choices'][0]['message'].get('content'))
    else:
        print(f"Error {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    summarize_storyline_force()
