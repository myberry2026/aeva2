import requests
import base64
import json
import os
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"
IMG1 = "logs/run_20260510_194221/step_1_before.png"
IMG2 = "logs/run_20260510_194221/step_1_after.png"

def call_remote(prompt, image_paths=[]):
    user_content = []
    for path in image_paths:
        with open(path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })
    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a specialized Android automation robot. Respond briefly."},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0
    }

    start_time = time.time()
    try:
        response = requests.post(URL, json=payload, timeout=120)
        duration = time.time() - start_time
        res_json = response.json()
        usage = res_json.get("usage")
        return duration, usage
    except Exception as e:
        return 0, {"error": str(e)}

def run_multi_image_comparison():
    # Get the real log prompt
    with open("verify_with_log_data.py", "r") as f:
        content = f.read()
        import re
        prompt_match = re.search(r'PROMPT = """(.*?)"""', content, re.DOTALL)
        long_prompt = prompt_match.group(1) if prompt_match else "Long prompt error"

    print("[*] Running Case 1: Real Log + 0 Images...")
    d0, u0 = call_remote("RND: " + str(time.time()) + "_A\n" + long_prompt, [])

    print("[*] Running Case 2: Real Log + 1 Image...")
    d1, u1 = call_remote("RND: " + str(time.time()) + "_B\n" + long_prompt, [IMG1])

    print("[*] Running Case 3: Real Log + 2 Images...")
    d2, u2 = call_remote("RND: " + str(time.time()) + "_C\n" + long_prompt, [IMG1, IMG2])

    print("\n" + "="*95)
    print(f"{'Input Mode (Real Log)':<30} | {'Duration':<10} | {'Prompt':<8} | {'Compl':<8} | {'Total':<8}")
    print("-" * 95)
    cases = [
        ("TEXT ONLY (0 Img)", d0, u0),
        ("TEXT + 1 IMAGE", d1, u1),
        ("TEXT + 2 IMAGES", d2, u2)
    ]
    for name, d, u in cases:
        p = u.get("prompt_tokens", "?")
        c = u.get("completion_tokens", "?")
        t = u.get("total_tokens", "?")
        print(f"{name:<30} | {d:>8.2f}s | {p:>8} | {c:>8} | {t:>8}")
    print("-" * 95)
    
    # Analysis
    img_token_cost = u1.get('prompt_tokens', 0) - u0.get('prompt_tokens', 0)
    img2_token_cost = u2.get('prompt_tokens', 0) - u1.get('prompt_tokens', 0)
    print(f"PER IMAGE TOKEN COST: ~{img_token_cost} (1st), ~{img2_token_cost} (2nd)")
    print(f"TOTAL MULTI-IMAGE OVERHEAD: +{d2 - d0:.2f}s Latency compared to text only")
    print("="*95)

if __name__ == "__main__":
    run_multi_image_comparison()
