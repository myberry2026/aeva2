import requests
import json
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def call_with_thinking(thinking_value):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Do NOT think, just answer directly."},
            {"role": "user", "content": "Explain why the sky is blue. Keep it very short."}
        ],
        "temperature": 0,
        "include_reasoning": thinking_value
    }
    
    print(f"\n--- Testing with thinking={thinking_value} ---")
    start_time = time.time()
    try:
        response = requests.post(URL, json=payload, timeout=60)
        duration = time.time() - start_time
        print(f"Status Code: {response.status_code}")
        print(f"Duration: {duration:.2f}s")
        if response.status_code == 200:
            res_json = response.json()
            message = res_json['choices'][0]['message']
            content = message.get("content", "")
            reasoning = message.get("reasoning_content", "")
            usage = res_json.get("usage", {})
            
            print(f"Content: {content.strip()}")
            if reasoning:
                print(f"Reasoning Length: {len(reasoning)} chars")
            else:
                print("No Reasoning Content found.")
            print(f"Usage: {usage}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    call_with_thinking(True)
    call_with_thinking(False)
    # Also try without the parameter at all
    print("\n--- Testing without thinking parameter ---")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "Explain the significance of the number 42."}
        ],
        "temperature": 0.7
    }
    start_time = time.time()
    response = requests.post(URL, json=payload, timeout=60)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"Response (first 200 chars): {response.json()['choices'][0]['message'].get('content', '')[:200]}...")
