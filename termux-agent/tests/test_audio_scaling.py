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
    sample_rate = 8000 # Lower sample rate
    num_samples = int(sample_rate * duration_sec)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            value = 0
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_scaling():
    durations = [0.01, 0.05, 0.1]
    print(f"--- Scaling Test for {MODEL} ---")
    
    for d in durations:
        filename = f"test_{d}.wav"
        generate_noise(filename, duration_sec=d)
        audio_b64 = encode_file(filename)
        
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": f"data:audio/wav;base64,{audio_b64}\n\nOk"}],
            "temperature": 0
        }
        
        try:
            r = requests.post(URL, json=payload, timeout=30)
            if r.status_code == 200:
                usage = r.json().get("usage", {})
                print(f"Duration: {d}s | Prompt Tokens: {usage.get('prompt_tokens')}")
            else:
                print(f"Duration: {d}s | Error: {r.text[:100]}")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

if __name__ == "__main__":
    test_scaling()
