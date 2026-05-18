import requests
import base64
import json
import os
import sys
import time

# 配置
URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def send_images(image_paths, prompt="What do you see in these images?"):
    print(f"[*] Preparing to send {len(image_paths)} images to {MODEL}...")
    
    user_content = []
    for i, path in enumerate(image_paths):
        print(f"    - Encoding image {i+1}: {path}")
        b64 = encode_image(path)
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })
    
    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2
    }

    print(f"[*] Sending request...")
    start_time = time.time()
    try:
        response = requests.post(URL, json=payload, timeout=120)
        duration = time.time() - start_time
        if response.status_code == 200:
            print(f"✅ Success! Latency: {duration:.2f}s")
            res = response.json()
            content = res['choices'][0]['message'].get('content', '')
            print(f"\n--- Model Response ---\n{content}\n")
            print(f"Usage: {res.get('usage')}")
        else:
            print(f"❌ Failed. Status: {response.status_code}, Error: {response.text}")
    except Exception as e:
        print(f"🔥 Error: {e}")

if __name__ == "__main__":
    # 使用示例: python send_gemma_images.py img1.png img2.png ...
    if len(sys.argv) < 2:
        print("Usage: python send_gemma_images.py <image_path1> [image_path2] ...")
        # 默认找几张图跑一下作为演示
        from glob import glob
        test_imgs = glob("screenshots/*.png")[:3]
        if test_imgs:
            print(f"No args provided, using default images: {test_imgs}")
            send_images(test_imgs)
        else:
            print("No images found in screenshots/ directory.")
    else:
        send_images(sys.argv[1:])
