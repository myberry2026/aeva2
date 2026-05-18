import requests
import base64
import os

# Configuration
URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"
AUDIO_FILE = "test_audio_chat.wav"

def encode_audio(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_audio_as_image_url():
    """
    HACK: Testing if we can bypass the Proxy filter by labeling audio as 'image_url'
    while keeping the 'audio/wav' mime type in the Data URI.
    """
    if not os.path.exists(AUDIO_FILE):
        print(f"Error: {AUDIO_FILE} not found.")
        return
        
    audio_b64 = encode_audio(AUDIO_FILE)
    print(f"\n--- Testing Audio disguised as 'image_url' ---")
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Listen to this audio and transcribe it."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:audio/wav;base64,{audio_b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0
    }
    
    try:
        r = requests.post(URL, json=payload, timeout=60)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print(f"Response: {r.json()['choices'][0]['message'].get('content')}")
        else:
            print(f"Error: {r.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_audio_as_image_url()
