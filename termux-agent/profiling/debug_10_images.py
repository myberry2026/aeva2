import requests
import base64
import os
import json

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def debug_10():
    imgs = []
    for root, dirs, files in os.walk("screenshots"):
        for f in files:
            if f.endswith(".png"):
                imgs.append(os.path.join(root, f))
                if len(imgs) >= 10: break
        if len(imgs) >= 10: break

    user_content = []
    for p in imgs:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encode_image(p)}"}
        })
    user_content.append({"type": "text", "text": "Describe each image briefly."})

    print(f"[*] Sending 10 images, total b64 size: {sum(os.path.getsize(p) for p in imgs)/1024/1024:.2f} MB")
    
    resp = requests.post(URL, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 500
    }, timeout=120)
    
    if resp.status_code == 200:
        data = resp.json()
        content = data['choices'][0]['message'].get('content', '')
        usage = data.get('usage', {})
        print(f"[*] Success!")
        print(f"[*] Usage: {usage}")
        print(f"[*] Content length: {len(content)}")
        print(f"[*] Content (first 500 chars): \n{content[:500]}")
    else:
        print(f"[*] Failed: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    debug_10()
