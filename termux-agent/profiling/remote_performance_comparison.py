import requests
import base64
import json
import os
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"
IMAGE_PATH = "logs/run_20260510_194221/step_1_before.png"

def call_remote(prompt, image_path=None):
    user_content = []
    if image_path:
        with open(image_path, "rb") as f:
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
        response = requests.post(URL, json=payload, timeout=60)
        duration = time.time() - start_time
        res_json = response.json()
        usage = res_json.get("usage")
        return duration, usage
    except Exception as e:
        return 0, {"error": str(e)}

def run_comparison():
    # Case 1: Minimal Text Only
    print("[*] Running Case 1: Minimal Text Only...")
    d1, u1 = call_remote("What is San Francisco famous for?")
    
    # Case 2: Minimal Text + Image
    print("[*] Running Case 2: Minimal Text + 1 Image...")
    d2, u2 = call_remote("What is in this image?", IMAGE_PATH)
    
    # Case 3: Real Log (Long Text) + Image
    print("[*] Running Case 3: Long Text (Real Log) + 1 Image...")
    with open("verify_with_log_data.py", "r") as f:
        # Extract the long prompt from the previous script
        content = f.read()
        import re
        prompt_match = re.search(r'PROMPT = """(.*?)"""', content, re.DOTALL)
        long_prompt = prompt_match.group(1) if prompt_match else "Long prompt error"
    
    d3, u3 = call_remote(long_prompt, IMAGE_PATH)

    print("\n" + "="*85)
    print(f"{'Test Case':<35} | {'Duration':<10} | {'Prompt':<8} | {'Compl':<8} | {'Total':<8}")
    print("-" * 85)
    cases = [
        ("1. Minimal Text Only", d1, u1),
        ("2. Minimal Text + 1 Image", d2, u2),
        ("3. Long Text (Log) + 1 Image", d3, u3)
    ]
    for name, d, u in cases:
        p = u.get("prompt_tokens", "?")
        c = u.get("completion_tokens", "?")
        t = u.get("total_tokens", "?")
        print(f"{name:<35} | {d:>8.2f}s | {p:>8} | {c:>8} | {t:>8}")
    print("="*85)

if __name__ == "__main__":
    run_comparison()
