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

def test_style_standard(audio_b64):
    """Testing standard OpenAI input_audio format"""
    print("\n--- Style A: Standard input_audio list ---")
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please transcribe or describe this audio."},
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
    send_request(payload)

def test_style_data_uri_string(audio_b64):
    """Testing Data URI embedded in string (previous known workaround)"""
    print("\n--- Style B: Data URI embedded in string ---")
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"data:audio/wav;base64,{audio_b64}\n\nPlease transcribe or describe this audio."
            }
        ],
        "temperature": 0
    }
    send_request(payload)

def test_style_legacy_images_field(audio_b64):
    """Testing if audio is accepted in the images field (some custom backends do this)"""
    print("\n--- Style C: Audio in 'images' field (HACK) ---")
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "Please transcribe or describe this audio."
            }
        ],
        "images": [audio_b64],
        "temperature": 0
    }
    send_request(payload)

def send_request(payload):
    try:
        response = requests.post(URL, json=payload, timeout=60)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            res_json = response.json()
            content = res_json['choices'][0]['message'].get('content', '')
            print(f"Response: {content}")
            if 'reasoning_content' in res_json['choices'][0]['message']:
                print(f"Reasoning: {res_json['choices'][0]['message']['reasoning_content']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    if not os.path.exists(AUDIO_FILE):
        print(f"Error: {AUDIO_FILE} not found in current directory.")
    else:
        b64 = encode_audio(AUDIO_FILE)
        test_style_standard(b64)
        test_style_data_uri_string(b64)
        test_style_legacy_images_field(b64)
