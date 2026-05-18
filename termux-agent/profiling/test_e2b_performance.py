import requests
import base64
import os
import time

# E2B 配置
URL = "http://localhost:8080/v1/chat/completions"
MODEL = "Gemma-4-E2B-it"

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

        start = time.time()
        try:
            resp = requests.post(URL, json={
                "model": MODEL,
                "messages": [{"role": "user", "content": user_content}],
                "max_tokens": 512
            }, timeout=60)
            dt = time.time() - start
            if resp.status_code == 200:
                usage = resp.json().get("usage", {})
                return dt, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
            else:
                print(f"Error {resp.status_code}: {resp.text}")
                return None, 0, 0
        except Exception as e:
            print(f"Exception: {e}")
            return None, 0, 0

    print(f"=== Gemma 4 E2B Performance Test ===")
    print(f"URL: {URL}")
    
    # 测 1 张
    d1, i1, o1 = call(1)
    # 测 10 张
    d10, i10, o10 = call(10)

    print("\n" + "="*80)
    print(f"{'Count':<8} | {'Lat (s)':<10} | {'In Tok':<10} | {'Out Tok':<10} | {'TPS':<10}")
    print("-" * 80)
    if d1:
        print(f"{1:<8} | {d1:>10.2f} | {i1:>10} | {o1:>10} | {o1/d1:>10.1f}")
    if d10:
        print(f"{10:<8} | {d10:>10.2f} | {i10:>10} | {o10:>10} | {o10/d10:>10.1f}")
    print("="*80)

if __name__ == "__main__":
    run_e2b_test()
