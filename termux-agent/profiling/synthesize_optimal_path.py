import os
import requests
import base64
import json
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"
LOGS_DIR = "logs"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_session_data(folder_name):
    folder_path = os.path.join(LOGS_DIR, folder_name)
    if not os.path.isdir(folder_path): return None
    
    # 找前两个和最后一个 step 的图
    files = sorted([f for f in os.listdir(folder_path) if f.endswith(".png")])
    if not files: return None
    
    sample_files = [files[0], files[min(1, len(files)-1)], files[-1]]
    images = []
    for f in sample_files:
        images.append(os.path.join(folder_path, f))
        
    return images

def synthesize_sessions():
    sessions = [
        "run_20260510_124542",
        "run_20260510_161629",
        "run_20260510_204339",
        "run_20260510_233351"
    ]
    
    all_images = []
    for s in sessions:
        imgs = get_session_data(s)
        if imgs: all_images.extend(imgs)
    
    print(f"[*] Total sampled images from 4 sessions: {len(all_images)}")
    
    user_content = []
    for img_p in all_images[:20]: # 最多 20 张
        user_content.append({
            "type": "image_url", 
            "image_url": {"url": f"data:image/png;base64,{encode_image(img_p)}"}
        })
    
    prompt = """You are an automation expert analyzing MULTIPLE sessions of the same task: 'Send SMS to 10086'.
I have provided snapshots from 4 different sessions. Some might start from the home screen, some from the app list, some from inside the thread.

Goal: Define ONE Universal Optimal Execution Path that works regardless of the starting state.

Please analyze:
1. State Detection: How to quickly distinguish if we are on 'Home', 'App List', or 'Inside Thread'?
2. Navigation: What is the most reliable way to get to the '10086' thread from any state?
3. Action: Re-confirm the best way to send the message.
4. Robustness: What checks should we perform to ensure we are not in the wrong state?

Provide a structured 'Master Script Logic' that handles all these variations."""

    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 4096,
        "extra_body": { "num_ctx": 64000 }
    }

    start = time.time()
    resp = requests.post(URL, json=payload, timeout=300)
    
    if resp.status_code == 200:
        print(f"\n[*] SUCCESS! {time.time()-start:.2f}s")
        print("\n" + "="*50 + " MASTER OPTIMAL PATH " + "="*50)
        print(resp.json()['choices'][0]['message'].get('content'))
        print("="*125)
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    synthesize_sessions()
