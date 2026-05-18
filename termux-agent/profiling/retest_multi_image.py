import requests
import base64
import json
import os
import time

# 配置
URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def get_test_images(count):
    images = []
    # 搜刮图片
    for root, dirs, files in os.walk("screenshots"):
        for f in files:
            if f.endswith((".png", ".jpg")):
                images.append(os.path.join(root, f))
                if len(images) >= count: return images
    if len(images) < count:
        for root, dirs, files in os.walk("logs"):
            for f in files:
                if f.endswith(".png") and "before" in f:
                    images.append(os.path.join(root, f))
                    if len(images) >= count: return images
    return images

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def call_gemma(count):
    imgs = get_test_images(count)
    user_content = []
    for p in imgs:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encode_image(p)}"}
        })
    user_content.append({"type": "text", "text": "Describe these images briefly."})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "temperature": 0.2
    }

    start = time.time()
    try:
        resp = requests.post(URL, json=payload, timeout=120)
        dt = time.time() - start
        if resp.status_code == 200:
            usage = resp.json().get("usage", {})
            return dt, usage.get("total_tokens", 0)
        return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def run_retest():
    print(f"=== Gemma 4 Multi-Image Retest (1 vs 10) ===")
    rounds = 3
    results_1 = []
    results_10 = []

    for i in range(rounds):
        print(f"\n[Round {i+1}] Testing 1 image...")
        dt, tokens = call_gemma(1)
        if dt: 
            print(f"    Done: {dt:.2f}s ({tokens} tokens)")
            results_1.append(dt)
        
        # 稍微歇一下，防止服务器缓存干扰
        time.sleep(2)

        print(f"[Round {i+1}] Testing 10 images...")
        dt, tokens = call_gemma(10)
        if dt:
            print(f"    Done: {dt:.2f}s ({tokens} tokens)")
            results_10.append(dt)
        
        time.sleep(2)

    avg_1 = sum(results_1)/len(results_1) if results_1 else 0
    avg_10 = sum(results_10)/len(results_10) if results_10 else 0

    print("\n" + "="*50)
    print(f"{'Scenario':<15} | {'Avg Latency (s)':<15}")
    print("-" * 50)
    print(f"{'1 Image':<15} | {avg_1:>15.2f}")
    print(f"{'10 Images':<15} | {avg_10:>15.2f}")
    print(f"Difference: {avg_10 - avg_1:.2f}s (仅增加了 {((avg_10/avg_1)-1)*100:.1f}%)")
    print("="*50)

if __name__ == "__main__":
    run_retest()
