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
            {"role": "system", "content": "You are a specialized Android automation robot. Do NOT output preamble."},
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
        content = res_json['choices'][0]['message'].get("content", "")
        return duration, usage, content
    except Exception as e:
        return 0, {"error": str(e)}, ""

def run_real_log_comparison():
    # Get the real log prompt
    with open("verify_with_log_data.py", "r") as f:
        content = f.read()
        import re
        prompt_match = re.search(r'PROMPT = """(.*?)"""', content, re.DOTALL)
        long_prompt = prompt_match.group(1) if prompt_match else "Long prompt error"

    # Case A: Real Log Text ONLY
    print("[*] Running Case A: Real Log (Long Text) ONLY...")
    d_text, u_text, c_text = call_remote(long_prompt, None)
    
    # Case B: Real Log Text + Image
    print("[*] Running Case B: Real Log (Long Text) + Image...")
    d_both, u_both, c_both = call_remote(long_prompt, IMAGE_PATH)

    print("\n" + "="*90)
    print(f"{'Input Mode (Real Log)':<30} | {'Duration':<10} | {'Prompt':<8} | {'Compl':<8} | {'Total':<8}")
    print("-" * 90)
    print(f"{'TEXT ONLY':<30} | {d_text:>8.2f}s | {u_text.get('prompt_tokens','?'):>8} | {u_text.get('completion_tokens','?'):>8} | {u_text.get('total_tokens','?'):>8}")
    print(f"{'TEXT + IMAGE':<30} | {d_both:>8.2f}s | {u_both.get('prompt_tokens','?'):>8} | {u_both.get('completion_tokens','?'):>8} | {u_both.get('total_tokens','?'):>8}")
    print("-" * 90)
    
    # Overhead analysis
    diff_tokens = u_both.get('prompt_tokens', 0) - u_text.get('prompt_tokens', 0)
    diff_time = d_both - d_text
    print(f"IMAGE OVERHEAD: +{diff_tokens} Tokens | +{diff_time:.2f}s Latency")
    print("="*90)

if __name__ == "__main__":
    run_real_log_comparison()
