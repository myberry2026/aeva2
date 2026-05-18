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
    
    total_duration = (duration_sec + gap_sec) * num_beeps
    print(f"[*] Generated {num_beeps} beeps: {filename} (Total duration: {total_duration:.2f}s)")

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_audio_reliability(num_beeps):
    filename = f"test_{num_beeps}_beeps.wav"
    generate_beeps(filename, num_beeps=num_beeps)
    audio_b64 = encode_file(filename)
    
    print(f"\n--- Reliability Test: Identifying {num_beeps} beeps ---")
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"data:audio/wav;base64,{audio_b64}\n\nHow many beeps? Answer with ONLY the digit."
            }
        ],
        "temperature": 0
    }
    
    try:
        response = requests.post(URL, json=payload, timeout=30)
        if response.status_code == 200:
            res_json = response.json()
            content = res_json['choices'][0]['message'].get("content", "").strip()
            print(f"AI Answer: {content}")
            return content
        else:
            print(f"❌ Failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_audio_reliability(1)
    test_audio_reliability(3)
