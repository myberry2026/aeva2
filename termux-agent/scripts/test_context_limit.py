import requests
import json
import time
import os
import sys

# URL and Model config
REMOTE_URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL_NAME = "google/gemma-4-e4b"

def log(msg):
    print(f"[*] {msg}", flush=True)

def test_context_length(target_tokens, max_tokens=1024):
    """
    Sends a request with roughly target_tokens to see how the LLM handles it.
    """
    log(f"Testing with target prompt tokens: {target_tokens}, max_tokens: {max_tokens}")
    
    # 1 token is roughly 4 characters for English text. 
    junk_text = "This is a test sentence to fill up the context. " * (target_tokens // 10)
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Please give a long response summarizing the importance of context windows."},
            {"role": "user", "content": junk_text + "\n\nEnd of junk. Now please provide a detailed explanation (at least 200 words) about context windows."}
        ],
        "stream": False,
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }

    t0 = time.time()
    try:
        log(f"Sending request (Payload size: {len(json.dumps(payload))/1024:.2f} KB)...")
        response = requests.post(REMOTE_URL, json=payload, timeout=120)
        dt = time.time() - t0
        
        if response.status_code != 200:
            log(f"FAILED: Status {response.status_code}")
            log(f"Error Detail: {response.text}")
            return False, None
        
        res_json = response.json()
        usage = res_json.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        content = res_json['choices'][0]['message'].get('content', '').strip()
        log(f"SUCCESS: {dt:.2f}s | Usage(in/out/total): {prompt_tokens}/{completion_tokens}/{total_tokens}")
        log(f"Response Length: {len(content)} chars")
        
        return True, usage
    except Exception as e:
        log(f"ERROR: {e}")
        return False, None

def main():
    log("=== Context Length & Generation Stress Test ===")
    log(f"Target URL: {REMOTE_URL}")
    log(f"Model: {MODEL_NAME}")
    
    # Test cases: (prompt_tokens, max_tokens)
    test_cases = [
        (1000, 512),
        (2000, 1024),
        (3500, 1024),
        (4000, 1024),
    ]
    
    results = []
    for pt, mt in test_cases:
        success, usage = test_context_length(pt, mt)
        if not success:
            log(f"Stopped at prompt={pt}, max_tokens={mt} due to failure.")
            # Let's try one more with very small max_tokens to see if it's the TOTAL that matters
            log("Retrying with minimal max_tokens=1 to isolate prompt limit...")
            test_context_length(pt, 1)
            break
        results.append(usage)
        time.sleep(1)

    log("\n=== Final Summary ===")
    for r in results:
        log(f"Prompt: {r.get('prompt_tokens')}, Completion: {r.get('completion_tokens')}, Total: {r.get('total_tokens')}")

if __name__ == "__main__":
    main()
