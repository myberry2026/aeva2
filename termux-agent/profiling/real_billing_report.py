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

def run_real_test():
    # 1. 抓 10 张不同的图
    all_imgs = []
    for root, dirs, files in os.walk("logs"):
        for f in files:
            if f.endswith(".png") and "before" in f:
                all_imgs.append(os.path.join(root, f))
                if len(all_imgs) >= 10: break
        if len(all_imgs) >= 10: break
    
    if len(all_imgs) < 10:
        print(f"Warning: Only found {len(all_imgs)} images.")

    def test_one_scenario(count):
        imgs = all_imgs[:count]
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
            "temperature": 0.2,
            "max_tokens": 512,
            "extra_body": {"enable_thinking": False} # 强制关掉思考，只要输出
        }

        start = time.time()
        resp = requests.post(URL, json=payload, timeout=120)
        dt = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            content = data['choices'][0]['message'].get('content', '')
            usage = data.get('usage', {})
            return {
                "latency": dt,
                "in": usage.get("prompt_tokens"),
                "out": usage.get("completion_tokens"),
                "chars": len(content),
                "text": content
            }
        return None

    print(f"=== Gemma 4 REAL BILLING REPORT ===")
    res1 = test_one_scenario(1)
    res10 = test_one_scenario(10)

    print("\n" + "="*110)
    print(f"{'Count':<8} | {'Lat (s)':<8} | {'In Tok':<10} | {'Out Tok':<10} | {'Chars':<10} | {'In TPS':<10} | {'Out TPS':<10}")
    print("-" * 110)
    for r, c in [(res1, 1), (res10, 10)]:
        if r:
            in_tps = r['in'] / r['latency']
            out_tps = r['out'] / r['latency']
            print(f"{c:<8} | {r['latency']:>8.2f} | {r['in']:>10} | {r['out']:>10} | {r['chars']:>10} | {in_tps:>10.1f} | {out_tps:>10.1f}")
    print("="*110)

if __name__ == "__main__":
    run_real_test()
