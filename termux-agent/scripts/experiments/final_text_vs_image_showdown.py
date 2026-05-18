import requests
import base64
import json
import os
import time
import sys

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"
IMG1 = "data/screenshots/maps_test.png"
IMG2 = "data/screenshots/chrome_test.png"

# We use a very long, unique text block for each case to simulate a real "heavy" prompt
LONG_TEXT_BASE = """
You are analyzing a complex Android system log and UI inventory. 
System State: Running. Battery: 85%. Network: WiFi.
UI Hierarchy Snapshot:
- Root (com.android.systemui)
  - FrameLayout [0,0][1080,2400]
    - View (Status Bar) [0,0][1080,84]
    - ViewGroup (Navigation Bar) [0,2316][1080,2400]
  - ViewGroup (Current App: com.google.android.apps.maps)
    - RelativeLayout [0,84][1080,2316]
      - Button (Search) id:search_bar [42,126][1038,252]
      - View (Map Surface) [0,0][1080,2400]
      - ImageButton (My Location) id:my_location [912,2064][1038,2190]
      - HorizontalScrollView (Categories) [0,273][1080,420]
        - Chip (Restaurants) [32,294][245,399]
        - Chip (Coffee) [266,294][432,399]
        - Chip (Hotels) [453,294][620,399]
        - Chip (Gas) [641,294][768,399]
... (Repeating to increase token count) ...
""" * 5 # Make it ~1500 tokens

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
            {"role": "system", "content": "You are a specialized Android intelligence agent. Respond in JSON."},
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

def run_final_showdown():
    # Case 0: Pure Long Text
    print("[*] Running Case 0: Pure LONG TEXT (0 Imgs)...")
    p0 = f"RND_{time.time()}_A\nTASK: Analyze the UI hierarchy below and find the coordinates of the 'Coffee' chip.\n{LONG_TEXT_BASE}"
    d0, u0 = call_remote(p0, [])
    
    # Case 1: Long Text + 1 Image
    print("[*] Running Case 1: LONG TEXT + 1 IMAGE...")
    p1 = f"RND_{time.time()}_B\nTASK: Compare the textual UI hierarchy below with the provided screenshot. Does the screenshot match the text?\n{LONG_TEXT_BASE}"
    d1, u1 = call_remote(p1, [IMG1])
    
    # Case 2: Long Text + 2 Images
    print("[*] Running Case 2: LONG TEXT + 2 IMAGES...")
    p2 = f"RND_{time.time()}_C\nTASK: Using the text and the two screenshots, identify which screenshot contains the elements described in the text.\n{LONG_TEXT_BASE}"
    d2, u2 = call_remote(p2, [IMG1, IMG2])

    print("\n" + "="*95)
    print(f"{'Input Mode (1500+ Tokens)':<30} | {'Duration':<10} | {'Prompt':<8} | {'Compl':<8} | {'Total':<8}")
    print("-" * 95)
    cases = [
        ("PURE TEXT ONLY", d0, u0),
        ("TEXT + 1 IMAGE", d1, u1),
        ("TEXT + 2 IMAGES", d2, u2)
    ]
    for name, d, u in cases:
        p = u.get("prompt_tokens", "?")
        c = u.get("completion_tokens", "?")
        t = u.get("total_tokens", "?")
        print(f"{name:<30} | {d:>8.2f}s | {p:>8} | {c:>8} | {t:>8}")
    print("="*95)

if __name__ == "__main__":
    run_final_showdown()
