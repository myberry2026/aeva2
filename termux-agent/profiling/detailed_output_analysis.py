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
    for root, dirs, files in os.walk("screenshots"):
        for f in files:
            if f.endswith((".png", ".jpg")):
                images.append(os.path.join(root, f))
                if len(images) >= count: return images
    return images

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def call_gemma_detailed(count):
    imgs = get_test_images(count)
    user_content = []
    for p in imgs:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encode_image(p)}"}
        })
    user_content.append({"type": "text", "text": "Please provide a very detailed description of everything you see in these images. Be extremely verbose."})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "temperature": 0.2,
        "max_tokens": 1024
    }

    start = time.time()
    try:
        resp = requests.post(URL, json=payload, timeout=120)
        dt = time.time() - start
        if resp.status_code == 200:
            res_json = resp.json()
            usage = res_json.get("usage", {})
            content = res_json['choices'][0]['message'].get('content', '')
            return {
                "latency": dt,
                "in_tokens": usage.get("prompt_tokens", 0),
                "out_tokens": usage.get("completion_tokens", 0),
                "char_count": len(content),
                "content": content
            }
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def run_detailed_report():
    print(f"=== Gemma 4 Detailed Output Analysis ===")
    
    scenarios = [1, 10]
    final_data = []

    for count in scenarios:
        print(f"\n[*] Testing {count} image(s)... (Requesting verbose output)")
        res = call_gemma_detailed(count)
        if res:
            res['count'] = count
            final_data.append(res)
            print(f"    Done! {res['latency']:.2f}s")

    print("\n" + "="*110)
    print(f"{'Images':<8} | {'Lat (s)':<8} | {'In Tok':<10} | {'Out Tok':<10} | {'Out Chars':<10} | {'Out TPS':<10} | {'Chars/s':<10}")
    print("-" * 110)
    
    for r in final_data:
        out_tps = r['out_tokens'] / r['latency']
        chars_s = r['char_count'] / r['latency']
        print(f"{r['count']:<8} | {r['latency']:>8.2f} | {r['in_tokens']:>10} | {r['out_tokens']:>10} | {r['char_count']:>10} | {out_tps:>10.1f} | {chars_s:>10.1f}")
    
    print("="*110)
    
    for r in final_data:
        print(f"\n[Sample Output for {r['count']} image(s)]:\n{r['content'][:300]}...")

if __name__ == "__main__":
    run_detailed_report()
