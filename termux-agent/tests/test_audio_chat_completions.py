import requests
import base64
import json
import wave
import struct
import math
import os

# Configuration
URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def generate_test_wav(filename, duration_sec=0.1, freq=440.0):
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            value = int(32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_audio_chat():
    audio_path = "test_audio_chat.wav"
    generate_test_wav(audio_path)
    audio_b64 = encode_file(audio_path)
    
    print(f"--- Testing Audio via /v1/chat/completions (Embedded in Text Field) ---")
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"data:audio/wav;base64,{audio_b64}\n\nWhat is this sound? Respond briefly."
            }
        ],
        "temperature": 0
    }
    
    try:
        response = requests.post(URL, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            res_json = response.json()
            content = res_json['choices'][0]['message'].get("content", "")
            print("✅ Success!")
            print(f"Response: {content}")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    # Variant 2: Separate text parts
    print(f"\n--- Testing Audio via /v1/chat/completions (Separate Text Parts) ---")
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"data:audio/wav;base64,{audio_b64}"},
                    {"type": "text", "text": "What is this sound? Respond briefly."}
                ]
            }
        ],
        "temperature": 0
    }
    
    try:
        response = requests.post(URL, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            res_json = response.json()
            content = res_json['choices'][0]['message'].get("content", "")
            print("✅ Success!")
            print(f"Response: {content}")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_audio_chat()
