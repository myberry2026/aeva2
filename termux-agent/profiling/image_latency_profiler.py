import time
import base64
import requests
import json

MODEL_URL = "http://localhost:11434/v1/chat/completions"
MODEL_NAME = "gemma4:latest"

def call_with_images(num_images):
    img_path = "profile.png" # Existing file from previous run
    prompt = "Action: Click 'Search'. List: ID 0: Search"
    
    user_content = [{"type": "text", "text": prompt}]
    for _ in range(num_images):
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": user_content}],
        "temperature": 0,
        "stream": False
    }

    start = time.time()
    try:
        response = requests.post(MODEL_URL, json=payload, timeout=120)
        duration = time.time() - start
        return duration, response.json().get('usage', {})
    except Exception as e:
        return 0, {"error": str(e)}

def run_comparison():
    print(f"[*] Starting Image vs Latency Profiling...\n")
    
    print("[Test 1] Pure Text (0 Images)...")
    t0, u0 = call_with_images(0)
    print(f" -> Latency: {t0:.2f}s")

    print("[Test 2] Decision Mode (1 Image)...")
    t1, u1 = call_with_images(1)
    print(f" -> Latency: {t1:.2f}s")

    print("[Test 3] Verification Mode (2 Images)...")
    t2, u2 = call_with_images(2)
    print(f" -> Latency: {t2:.2f}s")

    print("\n" + "="*30)
    print("IMAGE OVERHEAD ANALYSIS")
    print("="*30)
    print(f"Text Only:    {t0:.2f}s")
    print(f"1 Image Add:  {t1-t0:.2f}s")
    print(f"2 Images Add: {t2-t0:.2f}s")
    print("="*30)

if __name__ == "__main__":
    run_comparison()
