import requests
import json
import base64

url = "http://100.113.214.52:1234/v1/responses"

with open("test.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

payload = {
    "model": "google/gemma-4-e4b",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image? Return JSON {'description': '...'}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
            ]
        }
    ]
}

try:
    response = requests.post(url, json=payload, timeout=30)
    print(response.status_code)
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Exception: {e}")
