import requests
import json
import base64

def test_responses_api():
    url = "http://100.113.214.52:1234/v1/responses"
    model = "google/gemma-4-e4b"

    payload = {
        "model": model,
        "input": "Hello, who are you? Please respond in JSON format like {'name': '...'}.",
        "tool_choice": "auto"
    }

    print(f"Testing URL: {url}")
    print(f"Testing Model: {model}")

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
    test_responses_api()
