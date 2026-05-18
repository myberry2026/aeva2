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

def generate_tone(filename, duration_sec=0.01, freq=1000.0):
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

def test_ollama_style_audio():
    filename = "test_ollama.wav"
    generate_tone(filename)
    audio_b64 = encode_file(filename)
    
    print(f"--- Testing Ollama-style 'audio' field (Sibling to content) ---")
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "What is in this audio?",
                "audio": [audio_b64] # Sibling to content
            }
        ],
        "temperature": 0
    }
    
    try:
        r = requests.post(URL, json=payload, timeout=30)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print(f"✅ Success! Response: {r.json()['choices'][0]['message']['content'][:100]}...")
            print(f"Usage: {r.json().get('usage')}")
        else:
            print(f"❌ Failed: {r.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_ollama_style_audio()
