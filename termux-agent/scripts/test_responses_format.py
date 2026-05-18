import requests
import json
import base64

url = "http://100.113.214.52:1234/v1/responses"

with open("test.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

payload = {"model": "google/gemma-4-e4b", "input": "What's in this image? Return JSON {'description': '...'}", "images": [f"data:image/png;base64,{b64}"]}

response = requests.post(url, json=payload, timeout=30)
print(json.dumps(response.json(), indent=2))
