import requests
import base64
import json
import os
import time
import sys

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
        # Use a fresh session for each call to avoid connection reuse benefits
        with requests.Session() as session:
            response = session.post(URL, json=payload, timeout=120)
            duration = time.time() - start_time
            res_json = response.json()
            usage = res_json.get("usage")
            return duration, usage
    except Exception as e:
        return 0, {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python independent_test.py [0|1|2]")
        sys.exit(1)
    
    num_imgs = int(sys.argv[1])
    # Load real log prompt
    with open("verify_with_log_data.py", "r") as f:
        content = f.read()
        import re
        prompt_match = re.search(r'PROMPT = """(.*?)"""', content, re.DOTALL)
        long_prompt = prompt_match.group(1) if prompt_match else "Long prompt error"
    
    # Prepend random text for absolute cache bypass
    final_prompt = f"RND_{time.time()}_{num_imgs}\n{long_prompt}"
    
    imgs = [IMG1, IMG2][:num_imgs]
    print(f"[*] Running Case: {num_imgs} Images...")
    duration, usage = call_remote(final_prompt, imgs)
    
    result = {
        "case": f"{num_imgs} Images",
        "duration": f"{duration:.2f}s",
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens")
    }
    print(json.dumps(result, indent=2))
