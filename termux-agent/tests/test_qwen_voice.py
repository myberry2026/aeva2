import requests
import base64
import json
import wave
import struct
import math
import os
import time

# Configuration
URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "qwen35-9b-voice-v2"

def generate_beeps(filename, num_beeps=2, duration_sec=0.1, freq=1000.0, gap_sec=0.1):
    sample_rate = 16000
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for _ in range(num_beeps):
            num_samples = int(sample_rate * duration_sec)
            for i in range(num_samples):
                value = int(32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
                data = struct.pack('<h', value)
                wav_file.writeframesraw(data)
            num_gap_samples = int(sample_rate * gap_sec)
            for _ in range(num_gap_samples):
                wav_file.writeframesraw(struct.pack('<h', 0))

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_voice_model():
    filename = "test_voice.wav"
    generate_beeps(filename)
    audio_b64 = encode_file(filename)
    
    print(f"\n--- Testing Voice Model ({MODEL}) via Chat Completions ---")
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"data:audio/wav;base64,{audio_b64}\n\nWhat is in this audio?"
            }
        ],
        "temperature": 0
    }
    
    try:
        response = requests.post(URL, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Success!")
            print(f"Response: {response.json()['choices'][0]['message'].get('content')}")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_voice_model()
