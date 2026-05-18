import requests
import base64
import os
import json
import time
from PIL import Image
import io

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"
FOLDER = "logs/run_20260510_174510"
LOG_DIR = "profiling/raw_api_logs"

def encode_and_resize(path, size=(512, 512)):
    img = Image.open(path)
    img.thumbnail(size) # 等比例缩放，确保不超限
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def summarize_storyline_compressed():
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 选 20 张图
    imgs = []
    for i in range(1, 11):
        b = os.path.join(FOLDER, f"step_{i}_before.png")
        a = os.path.join(FOLDER, f"step_{i}_after.png")
        if os.path.exists(b): imgs.append(b)
        if os.path.exists(a): imgs.append(a)
    
    print(f"[*] Preparing {len(imgs)} COMPRESSED images for storyline analysis...")

    user_content = []
    for p in imgs:
        # 使用压缩后的 base64
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_and_resize(p)}"}})
    
    prompt = """These images are a chronological sequence of an Android automation experiment. 
Summarize the storyline: What was the goal, what happened in the middle, and what was the result?"""

    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 2048,
        "temperature": 0.2
    }

    print(f"[*] Sending compressed request (20 images) to {MODEL}...")
    start = time.time()
    resp = requests.post(URL, json=payload, timeout=300)
    dt = time.time() - start
    
    if resp.status_code == 200:
        res_data = resp.json()
        with open(f"{LOG_DIR}/storyline_compressed_response.json", "w", encoding="utf-8") as f:
            json.dump(res_data, f, indent=2, ensure_ascii=False)
        
        msg = res_data['choices'][0]['message']
        print(f"\n[*] SUCCESS! Latency: {dt:.2f}s")
        print("\n" + "="*50 + " COMPRESSED STORYLINE SUMMARY " + "="*50)
        print(f"\n[REPLY]\n{msg.get('content', '')}")
        print("="*119)
    else:
        print(f"Error {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    summarize_storyline_compressed()
