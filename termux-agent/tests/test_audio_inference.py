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

def test_inference_only():
    filename = "test_inf.wav"
    generate_tone(filename)
    audio_b64 = encode_file(filename)
    
    print(f"--- Inference Only Test for {MODEL} ---")
    
    # We send a long tone and ask for its frequency
    generate_tone(filename, duration_sec=0.1, freq=2000.0)
    audio_b64 = encode_file(filename)
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"data:audio/wav;base64,{audio_b64}\n\nIs this a high-pitched tone or a low-pitched tone?"
            }
        ],
        "temperature": 0
    }
    
    try:
        r = requests.post(URL, json=payload, timeout=30)
        print(f"Response: {r.json()['choices'][0]['message']['content']}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_inference_only()
