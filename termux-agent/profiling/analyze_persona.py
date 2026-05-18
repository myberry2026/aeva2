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

def analyze_persona():
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
    
    prompt = """These 20 images show a user's interaction session. 
Beyond just describing the actions, please perform a 'User Persona & Experience Analysis':
1. Who is this person? (Professional background, technical level, interests based on UI/Apps)
2. What are they experiencing right now? (What is their immediate problem or goal?)
3. What is their emotional or cognitive state during this sequence?
Provide a deep psychological and professional profile based on these visual cues."""

    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 2048, 
        "temperature": 0.7, # 稍微调高一点温度，让它更有洞察力
        "extra_body": { "num_ctx": 64000 }
    }

    print(f"[*] Analyzing user persona from 20 images...")
    start = time.time()
    resp = requests.post(URL, json=payload, timeout=300)
    dt = time.time() - start
    
    if resp.status_code == 200:
        res_data = resp.json()
        content = res_data['choices'][0]['message'].get('content', '')
        print(f"\n[*] SUCCESS! Latency: {dt:.2f}s")
        print("\n" + "="*50 + " USER PERSONA & EXPERIENCE ANALYSIS " + "="*50)
        print(f"\n{content}")
        print("="*128)
    else:
        print(f"Error {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    analyze_persona()
