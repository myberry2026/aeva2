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
MODEL = "google/gemma-4-e4b"

def generate_tone(filename, duration_sec=0.01, freq=1000.0):
    sample_rate = 8000
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

def test_placeholder():
    filename = "test_placeholder.wav"
    generate_tone(filename)
    audio_b64 = encode_file(filename)
    
    print(f"--- Testing Placeholder Logic for {MODEL} ---")
    
    # Try multiple placeholders
    placeholders = ["<|audio|>", "[AUDIO]", "[[AUDIO]]", "{AUDIO}", "<audio>"]
    
    for p in placeholders:
        print(f"Testing placeholder: {p}")
        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": f"{p} data:audio/wav;base64,{audio_b64}\n\nWhat is this sound?"
                }
            ],
            "temperature": 0
        }
        
        try:
            r = requests.post(URL, json=payload, timeout=30)
            if r.status_code == 200:
                print(f"✅ Status: 200 | Response: {r.json()['choices'][0]['message']['content'][:100]}...")
            else:
                print(f"❌ Status: {r.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if os.path.exists(filename):
        os.remove(filename)

if __name__ == "__main__":
    test_placeholder()
