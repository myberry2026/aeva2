import requests
import base64
import os
import json
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"
LOG_DIR = "profiling/raw_api_logs"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def save_raw_interaction():
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 抓 10 张图
    all_imgs = []
    for root, dirs, files in os.walk("logs"):
        for f in files:
            if f.endswith(".png") and "before" in f:
                all_imgs.append(os.path.join(root, f))
                if len(all_imgs) >= 10: break
        if len(all_imgs) >= 10: break

    user_content = []
    for p in all_imgs:
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image(p)}"}})
    user_content.append({"type": "text", "text": "Describe these images."})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 1024,
        "temperature": 0.2
    }

    # 保存请求包 (Request)
    req_file = f"{LOG_DIR}/last_request.json"
    with open(req_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    print(f"[*] Sending request to {MODEL}...")
    start = time.time()
    resp = requests.post(URL, json=payload, timeout=120)
    dt = time.time() - start
    
    # 保存返回包 (Response)
    res_file = f"{LOG_DIR}/last_response.json"
    if resp.status_code == 200:
        res_data = resp.json()
        with open(res_file, "w", encoding="utf-8") as f:
            json.dump(res_data, f, indent=2, ensure_ascii=False)
        print(f"[*] Success! Latency: {dt:.2f}s")
        print(f"[*] RAW Request saved to: {req_file}")
        print(f"[*] RAW Response saved to: {res_file}")
    else:
        print(f"Error {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    save_raw_interaction()
