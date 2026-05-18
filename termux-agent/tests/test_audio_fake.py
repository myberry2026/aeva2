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

def generate_noise(filename, duration_sec=0.01):
    sample_rate = 8000
    num_samples = int(sample_rate * duration_sec)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for _ in range(num_samples):
            wav_file.writeframesraw(struct.pack('<h', 0))

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_no_audio_string():
    filename = "test_no_audio.wav"
    generate_noise(filename)
    audio_b64 = encode_file(filename)
    
    print(f"--- Testing String vs Real Audio for {MODEL} ---")
    
    # 1. Real Base64
    payload_real = {
        "model": MODEL,
        "messages": [{"role": "user", "content": f"data:audio/wav;base64,{audio_b64}\n\nOk"}],
        "temperature": 0
    }
    
    # 2. Fake Base64 (Random characters)
    fake_b64 = "AAAA" * 100
    payload_fake = {
        "model": MODEL,
        "messages": [{"role": "user", "content": f"data:audio/wav;base64,{fake_b64}\n\nOk"}],
        "temperature": 0
    }
    
    try:
        r_real = requests.post(URL, json=payload_real, timeout=30)
        r_fake = requests.post(URL, json=payload_fake, timeout=30)
        
        print(f"Real Audio Tokens: {r_real.json()['usage']['prompt_tokens']}")
        print(f"Fake Audio Tokens: {r_fake.json()['usage']['prompt_tokens']}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_no_audio_string()
