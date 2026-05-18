import requests
import base64
import os
import time

# 远端配置 (E2B)
URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def run_e2b_test():
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
        user_content.append({"type": "text", "text": "Describe these images briefly."})

        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": user_content}],
            "temperature": 0.2,
            "max_tokens": 512,
            "extra_body": {"enable_thinking": False}
        }

        start = time.time()
        try:
            resp = requests.post(URL, json=payload, timeout=60)
            dt = time.time() - start
            if resp.status_code == 200:
                data = resp.json()
                usage = data.get("usage", {})
                msg = data['choices'][0]['message']
                content = (msg.get('content') or '') + (msg.get('reasoning_content') or '')
                return dt, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), len(content)
            else:
                print(f"Error {resp.status_code}: {resp.text}")
                return None, 0, 0, 0
        except Exception as e:
            print(f"Exception: {e}")
            return None, 0, 0, 0

    print(f"=== Gemma 4 E2B (Remote) Performance Test ===")
    print(f"Target: {URL} | Model: {MODEL}")
    
    # 测 1 张
    d1, i1, o1, c1 = call(1)
    # 测 10 张
    d10, i10, o10, c10 = call(10)

    print("\n" + "="*90)
    print(f"{'Count':<8} | {'Lat (s)':<10} | {'In Tok':<10} | {'Out Tok':<10} | {'Chars':<10} | {'Out TPS':<10}")
    print("-" * 90)
    if d1:
        print(f"{1:<8} | {d1:>10.2f} | {i1:>10} | {o1:>10} | {c1:>10} | {o1/d1:>10.1f}")
    if d10:
        print(f"{10:<8} | {d10:>10.2f} | {i10:>10} | {o10:>10} | {c10:>10} | {o10/d10:>10.1f}")
    print("="*90)

if __name__ == "__main__":
    run_e2b_test()
