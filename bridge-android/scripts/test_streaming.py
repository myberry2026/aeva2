import requests
import json
import sys

def test_streaming():
    url = "http://localhost:8081/v1/chat/completions"
    payload = {
        "model": "Gemma-4-E2B-it",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "Write a short story about a robot learning to paint."}
        ],
        "stream": True,
        "temperature": 0.7
    }

    print("🚀 Starting Streaming Request...")
    try:
        response = requests.post(url, json=payload, stream=True, timeout=120)
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return

        print("\n[Response]:")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    if data_str == "[DONE]":
                        print("\n\n✅ Stream Finished.")
                        break
                    
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk['choices'][0]['delta']
                        if 'content' in delta:
                            content = delta['content']
                            print(content, end="", flush=True)
                        if 'reasoning_content' in delta:
                            reasoning = delta['reasoning_content']
                            # Print reasoning in italics or different color if supported
                            print(f"\n[Thinking: {reasoning}]", end="", flush=True)
                    except Exception as e:
                        pass
    except Exception as e:
        print(f"\nFailed: {e}")

if __name__ == "__main__":
    test_streaming()
