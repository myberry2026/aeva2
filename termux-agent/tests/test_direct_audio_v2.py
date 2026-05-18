import requests
import base64
import os

# Configuration
URL = "http://100.113.214.52:1234/v1/chat/completions"
# We will test both models
MODELS = ["google/gemma-4-e4b", "qwen35-9b-voice-v2"]
AUDIO_FILE = "test_audio_chat.wav"

def encode_audio(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_multimodal_audio_field(model_name, audio_b64):
    """
    Testing a top-level 'audios' field, which is common in some vLLM/multimodal implementations.
    """
    print(f"\n--- Testing '{model_name}' with top-level 'audios' field ---")
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "Please transcribe this audio."
            }
        ],
        "audios": [audio_b64],
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

def test_qwen_voice_openai_format(audio_b64):
    """
    Qwen-Voice often uses the standard OpenAI-like content list.
    """
    print(f"\n--- Testing 'qwen35-9b-voice-v2' with OpenAI content list ---")
    payload = {
        "model": "qwen35-9b-voice-v2",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this audio?"},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_b64,
                            "format": "wav"
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
    if os.path.exists(AUDIO_FILE):
        b64 = encode_audio(AUDIO_FILE)
        # Test Gemma with audios field
        test_multimodal_audio_field("google/gemma-4-e4b", b64)
        # Test Qwen with audios field
        test_multimodal_audio_field("qwen35-9b-voice-v2", b64)
        # Test Qwen with standard format (to see if Proxy allows it for THIS model)
        test_qwen_voice_openai_format(b64)
    else:
        print("Audio file not found.")
