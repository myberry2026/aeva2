import requests
import json
import time

def test_hermes_llm():
    base_url = "http://localhost:8081"
    
    print("--- Step 1: Checking Health ---")
    try:
        health = requests.get(f"{base_url}/health", timeout=5)
        print(f"Health Response: {json.dumps(health.json(), indent=2)}")
        if not health.json().get("model_loaded"):
            print("ERROR: Model is not loaded on the device! Please click [Load] in the app.")
            return
    except Exception as e:
        print(f"Connection Failed: {e}. Is the LLM Server (8080) started in the app?")
        return

    print("\n--- Step 2: Sending Chat Request ---")
    payload = {
        "model": "Gemma-4-E2B-it",
        "messages": [
            {"role": "user", "content": "Who are you? Please answer in 3 short sentences."}
        ]
    }
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            timeout=120 # Model inference can be slow
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            print(f"Success! (Took {elapsed:.2f}s)")
            print(f"\nModel Response:\n{'-'*20}\n{content}\n{'-'*20}")
        else:
            print(f"Server Error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_hermes_llm()
