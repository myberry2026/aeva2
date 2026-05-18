import requests
import base64
import os
import json

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def capture_full_text():
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
    user_content.append({"type": "text", "text": "What is in these images? Provide a comprehensive and detailed analysis."})

    print("[*] Requesting full text from model...")
    resp = requests.post(URL, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 4000
    }, timeout=300)
    
    if resp.status_code == 200:
        data = resp.json()
        msg = data['choices'][0]['message']
        thinking = msg.get('reasoning_content', 'No thinking provided.')
        reply = msg.get('content', 'No final reply provided.')
        
        full_text = f"=== THINKING PROCESS ===\n{thinking}\n\n=== FINAL REPLY ===\n{reply}"
        
        with open("profiling/model_output_full.txt", "w", encoding="utf-8") as f:
            f.write(full_text)
        
        print(f"[*] Done! Saved to profiling/model_output_full.txt")
        print("\n--- Snippet (First 2000 Chars) ---\n")
        print(full_text[:2000] + "...")
    else:
        print(f"Error: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    capture_full_text()
