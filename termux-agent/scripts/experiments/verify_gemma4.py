import requests
import base64
import json
import os
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def encode_image(image_path):
    if not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def call_gemma(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0
    }
    start_time = time.time()
    try:
        response = requests.post(URL, json=payload, timeout=60)
        duration = time.time() - start_time
        if response.status_code != 200:
            return f"Error: Status {response.status_code}, {response.text}", duration, None
        
        res_json = response.json()
        content = res_json['choices'][0]['message'].get("content", "")
        usage = res_json.get("usage")
        return content, duration, usage
    except Exception as e:
        return f"Error: {e}", 0, None

def verify():
    # 1. Text only
    print("--- Scenario 1: Text Only ---")
    messages = [
        {"role": "user", "content": "Hello, who are you? Please respond briefly."}
    ]
    content, duration, usage = call_gemma(messages)
    print(f"Response: {content}")
    print(f"Duration: {duration:.2f}s")
    print(f"Usage: {usage}")
    print()

    # 2. Text + 1 Image
    print("--- Scenario 2: Text + 1 Image ---")
    img1_path = "test.png"
    img1_b64 = encode_image(img1_path)
    if img1_b64:
        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img1_b64}"}}
                ]
            }
        ]
        content, duration, usage = call_gemma(messages)
        print(f"Response: {content}")
        print(f"Duration: {duration:.2f}s")
        print(f"Usage: {usage}")
    else:
        print(f"Skipping: {img1_path} not found.")
    print()

    # 3. Text + 2 Images
    print("--- Scenario 3: Text + 2 Images ---")
    img2_path = "profile.png"
    img2_b64 = encode_image(img2_path)
    if img1_b64 and img2_b64:
        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "Describe the differences between these two images briefly."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img1_b64}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img2_b64}"}}
                ]
            }
        ]
        content, duration, usage = call_gemma(messages)
        print(f"Response: {content}")
        print(f"Duration: {duration:.2f}s")
        print(f"Usage: {usage}")
    else:
        print(f"Skipping: {img1_path} or {img2_path} not found.")
    print()

if __name__ == "__main__":
    verify()
