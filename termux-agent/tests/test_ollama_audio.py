import requests
import base64
import json
import wave
import struct
import math
import os
import time

# Configuration
URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:latest"

def generate_beeps(filename, num_beeps=3, duration_sec=0.1, freq=1000.0, gap_sec=0.1):
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
    print(f"[*] Generated {num_beeps} beeps: {filename}")

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_ollama_native_audio(num_beeps):
    filename = f"test_ollama_{num_beeps}.wav"
    generate_beeps(filename, num_beeps=num_beeps)
    audio_b64 = encode_file(filename)
    
    print(f"\n--- Testing Local Ollama Native API: {num_beeps} beeps ---")
    
    # Try different formats for Ollama
    # 1. As 'images' (some multimodal models in Ollama use this even for audio)
    # 2. As 'audio' (newer standard)
    
    formats = [
        {"audio": [audio_b64]},
        {"images": [audio_b64]}
    ]
    
    for fmt in formats:
        print(f"Using payload key: {list(fmt.keys())[0]}")
        payload = {
            "model": MODEL,
            "prompt": "How many beeps are in this audio? Answer only with the digit.",
            "stream": False,
            **fmt
        }
        
        try:
            start_time = time.time()
            response = requests.post(URL, json=payload, timeout=60)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                res_json = response.json()
                print(f"✅ Status: 200 | Time: {duration:.2f}s")
                print(f"Response: {res_json.get('response', '').strip()}")
            else:
                print(f"❌ Failed (Status {response.status_code}): {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if os.path.exists(filename):
        os.remove(filename)

if __name__ == "__main__":
    test_ollama_native_audio(2)
