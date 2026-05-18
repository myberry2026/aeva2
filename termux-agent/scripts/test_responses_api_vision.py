import requests
import json
import base64

def test_responses_api_vision():
    url = "http://100.113.214.52:1234/v1/responses"
    model = "google/gemma-4-e4b"

    with open("test.png", "rb") as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')

    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What do you see in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]
            }
        ],
        "tool_choice": "auto"
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_responses_api_vision()
