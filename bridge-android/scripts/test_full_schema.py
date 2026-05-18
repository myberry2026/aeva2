import requests
import json
import time

def test_full_schema():
    url = "http://localhost:8081/v1/chat/completions"
    
    # 1. Test with System Prompt and Parameters
    print("--- Running Full Schema Test (System Prompt + Params) ---")
    payload = {
        "model": "Gemma-4-E2B-it",
        "temperature": 0.2, # Very creative or very focused?
        "top_p": 0.9,
        "messages": [
            {"role": "system", "content": "You are a professional chef. Answer everything in the style of a cooking recipe."},
            {"role": "user", "content": "How do I fix a broken heart?"}
        ]
    }
    
    try:
        start = time.time()
        response = requests.post(url, json=payload, timeout=120)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            # Reasoning content is a unique feature of Gemma-4
            reasoning = data["choices"][0]["message"].get("reasoning_content")
            
            print(f"Success! ({elapsed:.2f}s)")
            if reasoning:
                print(f"\n[Thinking]:\n{reasoning}\n")
            print(f"[Chef Gemma]:\n{content}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_full_schema()
