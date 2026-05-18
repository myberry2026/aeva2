import requests
import base64
import os
import json

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def inspect():
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
    user_content.append({"type": "text", "text": "What is in these images?"})

    print("[*] Requesting raw JSON...")
    resp = requests.post(URL, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 100
    })
    
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    inspect()
