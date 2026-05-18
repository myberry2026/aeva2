import requests
import base64
import os
import json
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def final_billing():
    # 抓图
    all_imgs = []
    for root, dirs, files in os.walk("logs"):
        for f in files:
            if f.endswith(".png") and "before" in f:
                all_imgs.append(os.path.join(root, f))
                if len(all_imgs) >= 10: break
        if len(all_imgs) >= 10: break

    def call(count):
        imgs = all_imgs[:count]
        user_content = []
        for p in imgs:
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image(p)}"}})
        user_content.append({"type": "text", "text": "Describe these images in detail."})

        start = time.time()
        resp = requests.post(URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": user_content}],
            "max_tokens": 8000
        }, timeout=300)
        dt = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            msg = data['choices'][0]['message']
            content = msg.get('content', '') or ''
            reasoning = msg.get('reasoning_content', '') or ''
            full_text = content + reasoning
            usage = data.get('usage', {})
            return {
                "latency": dt,
                "in": usage.get("prompt_tokens"),
                "out": usage.get("completion_tokens"),
                "chars": len(full_text),
                "out_tps": usage.get("completion_tokens") / dt
            }
        return None

    print(f"=== Gemma 4 FINAL SETTLEMENT REPORT (Including Reasoning) ===")
    r1 = call(1)
    r10 = call(10)

    print("\n" + "="*110)
    print(f"{'Count':<8} | {'Lat (s)':<8} | {'In Tok':<10} | {'Out Tok':<10} | {'Total Chars':<12} | {'Out TPS':<10}")
    print("-" * 110)
    for r, c in [(r1, 1), (r10, 10)]:
        if r:
            print(f"{c:<8} | {r['latency']:>8.2f} | {r['in']:>10} | {r['out']:>10} | {r['chars']:>12} | {r['out_tps']:>10.1f}")
    print("="*110)

if __name__ == "__main__":
    final_billing()
