import requests
import base64
import json
import wave
import struct
import math
import os

# Configuration (matching the project's defaults)
URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def generate_test_wav(filename, duration_sec=1.0, freq=440.0):
    """Generates a simple sine wave WAV file for testing."""
    sample_rate = 44100
    num_samples = int(sample_rate * duration_sec)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            value = int(32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)
    print(f"[*] Generated test audio: {filename}")

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_audio_format(name, content_item):
    print(f"\n--- Testing Format: {name} ---")
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "This is an audio file. Please describe what you hear or tell me if you can process it."},
                    content_item
                ]
            }
        ],
        "temperature": 0
    }
    
    try:
        response = requests.post(URL, json=payload, timeout=30)
        if response.status_code == 200:
            res_json = response.json()
            content = res_json['choices'][0]['message'].get("content", "")
            print(f"✅ Success!")
            print(f"Response: {content}")
        else:
            print(f"❌ Failed (Status {response.status_code})")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_transcriptions_api(audio_path):
    print(f"\n--- Testing Transcriptions API (/v1/audio/transcriptions) ---")
    url = URL.replace("/chat/completions", "/audio/transcriptions")
    try:
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path, f, "audio/wav")}
            data = {"model": "whisper-large-v3-turbo"}
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Success!")
                print(f"Response: {response.text}")
            else:
                print(f"❌ Failed (Status {response.status_code})")
                print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    audio_path = "test_audio.wav"
    generate_test_wav(audio_path)
    audio_b64 = encode_file(audio_path)

    # Test Transcriptions first
    test_transcriptions_api(audio_path)

    # Format 1: OpenAI GPT-4o style (input_audio)
    test_audio_format("input_audio (OpenAI Style)", {
        "type": "input_audio",
        "input_audio": {
            "data": audio_b64,
            "format": "wav"
        }
    })

    # Format 2: audio_url (Common Proxy Style)
    test_audio_format("audio_url (Proxy Style)", {
        "type": "audio_url",
        "audio_url": {
            "url": f"data:audio/wav;base64,{audio_b64}"
        }
    })

    # Format 3: image_url Hack (Passing audio via image field)
    test_audio_format("image_url Hack", {
        "type": "image_url",
        "image_url": {
            "url": f"data:audio/wav;base64,{audio_b64}"
        }
    })

    # Cleanup
    if os.path.exists(audio_path):
        os.remove(audio_path)
