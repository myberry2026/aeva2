import requests
import base64
import os
import json
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def compare_content():
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
        user_content.append({"type": "text", "text": "What is in these images? Provide a detailed and comprehensive analysis."})

        start = time.time()
        resp = requests.post(URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": user_content}],
            "max_tokens": 1024,
            "extra_body": {"enable_thinking": True} # 开启思考看全貌
        }, timeout=120)
        dt = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            msg = data['choices'][0]['message']
            thinking = msg.get('reasoning_content', '') or ''
            reply = msg.get('content', '') or ''
            usage = data.get('usage', {})
            tps = usage.get('completion_tokens', 0) / dt
            return {
                "latency": dt,
                "tps": tps,
                "full_text": f"--- THINKING ---\n{thinking}\n\n--- REPLY ---\n{reply}",
                "tokens": usage.get('completion_tokens')
            }
        return None

    print(f"=== E2B Content & Speed Comparison ===")
    
    print("\n" + "="*30 + " CASE 1: SINGLE IMAGE " + "="*30)
    res1 = call(1)
    if res1:
        print(f"Latency: {res1['latency']:.2f}s | Speed: {res1['tps']:.1f} TPS")
        print("\n[CONTENT SNIPPET]:")
        print(res1['full_text'][:1500] + "...")
    
    print("\n" + "="*30 + " CASE 2: TEN IMAGES " + "="*30)
    res10 = call(10)
    if res10:
        print(f"Latency: {res10['latency']:.2f}s | Speed: {res10['tps']:.1f} TPS")
        print("\n[CONTENT SNIPPET]:")
        print(res10['full_text'][:1500] + "...")

    print("\n" + "="*80)
    if res1 and res10:
        print(f"Summary: 1 Image ({res1['tps']:.1f} TPS) vs 10 Images ({res10['tps']:.1f} TPS)")
        if abs(res1['tps'] - res10['tps']) < 5:
            print("Verdict: Speeds are NEARLY THE SAME.")
        else:
            print(f"Verdict: Speed DROPPED by {res1['tps'] - res10['tps']:.1f} TPS with more images.")
    print("="*80)

if __name__ == "__main__":
    compare_content()
