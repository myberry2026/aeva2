import requests
import base64
import json
import os
import time
import sys

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

# New diverse cases using existing screenshots
RANDOM_CASES = [
    {
        "name": "Youtube Content Analysis (1 Img)",
        "prompt": f"RND_{time.time()}_Y\nLook at this video platform screenshot. What category of content is being displayed, and what are the specific recommendations visible? Respond in JSON with 'category' and 'items'.",
        "images": ["data/screenshots/youtube_test.png"]
    },
    {
        "name": "Settings vs SMS Comparison (2 Imgs)",
        "prompt": f"RND_{time.time()}_S\nIdentify which image is a system configuration screen and which is a communication interface. List the top three interactive items from each. Respond in JSON.",
        "images": ["data/screenshots/settings_test.png", "data/screenshots/sms_test.png"]
    },
    {
        "name": "App List Inventory (1 Img)",
        "prompt": f"RND_{time.time()}_A\nExamine this application drawer. List all the visible application names in alphabetical order. Respond in JSON with an 'apps' list.",
        "images": ["data/screenshots/step_5.png"] # step_5 usually has a dense app list or home screen
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
            {"role": "system", "content": "You are a specialized Android intelligence agent. Respond ONLY in raw JSON."},
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
            content = res_json['choices'][0]['message'].get("content", "")
            return duration, usage, content
    except Exception as e:
        return 0, {"error": str(e)}, ""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python random_cases_test.py [0|1|2]")
        sys.exit(1)
    
    idx = int(sys.argv[1])
    case = RANDOM_CASES[idx]
    
    print(f"[*] Running Random Case {idx}: {case['name']}...")
    duration, usage, content = call_remote(case['prompt'], case['images'])
    
    print(f"\n[Response Content]:\n{content}")
    result = {
        "case": case['name'],
        "duration": f"{duration:.2f}s",
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens")
    }
    print(f"\n[Stats]:\n{json.dumps(result, indent=2)}")
