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

def generate_beeps(filename, num_beeps=3, duration_sec=0.02, freq=1000.0, gap_sec=0.02):
    sample_rate = 8000
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

def test_audio_multimodal(num_beeps):
    filename = f"test_mm_{num_beeps}_beeps.wav"
    generate_beeps(filename, num_beeps=num_beeps)
    audio_b64 = encode_file(filename)
    
    print(f"\n--- Multimodal Format Test: Identifying {num_beeps} beeps ---")
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Listen to this audio. How many beeps? Answer with ONLY the digit."},
                    {
                        "type": "audio", # Some vLLM versions use 'audio' instead of 'input_audio'
                        "audio": f"data:audio/wav;base64,{audio_b64}"
                    }
                ]
            }
        ],
        "temperature": 0
    }
    
    try:
        response = requests.post(URL, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            content = response.json()['choices'][0]['message'].get("content", "").strip()
            print(f"AI Answer: {content}")
        else:
            print(f"❌ Failed: {response.text}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def test_input_audio_format(num_beeps):
    filename = f"test_ia_{num_beeps}_beeps.wav"
    generate_beeps(filename, num_beeps=num_beeps)
    audio_b64 = encode_file(filename)
    
    print(f"\n--- OpenAI input_audio Format Test: Identifying {num_beeps} beeps ---")
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "How many beeps? Digit only."},
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
        response = requests.post(URL, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            content = response.json()['choices'][0]['message'].get("content", "").strip()
            print(f"AI Answer: {content}")
        else:
            print(f"❌ Failed: {response.text}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_audio_multimodal(2)
    test_input_audio_format(2)
