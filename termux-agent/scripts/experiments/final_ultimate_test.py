import requests
import base64
import json
import os
import time
import sys

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

# Completely Unique Data for each case
CASES = [
    {
        "name": "0 IMAGES (Text Only)",
        "prompt": "Explain the step-by-step process of enabling Developer Options on an Android 14 device and how to find the USB Debugging toggle thereafter. Be technical and precise.",
        "images": []
    },
    {
        "name": "1 IMAGE (Unique Screenshot)",
        "prompt": "Analyze this specific mobile interface. Identify the main navigation tabs at the bottom and tell me what the 'Goal' of this screen seems to be based on the visible content.",
        "images": ["data/screenshots/step_1.png"]
    },
    {
        "name": "2 IMAGES (Two Different Screens)",
        "prompt": "You are looking at two different application states. Compare the visual density and the primary action buttons of the first image (top) versus the second image (bottom). Which one is more navigation-heavy?",
        "images": ["data/screenshots/maps_test.png", "data/screenshots/chrome_test.png"]
    }
]

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
            {"role": "system", "content": "You are a specialized mobile QA assistant. Respond concisely."},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0
    }

    start_time = time.time()
    try:
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
        print("Usage: python final_ultimate_test.py [0|1|2]")
        sys.exit(1)
    
    idx = int(sys.argv[1])
    case = CASES[idx]
    
    print(f"[*] Running Case {idx}: {case['name']}...")
    print(f"[*] Images: {case['images']}")
    
    duration, usage = call_remote(case['prompt'], case['images'])
    
    result = {
        "case": case['name'],
        "duration": f"{duration:.2f}s",
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens")
    }
    print(json.dumps(result, indent=2))
