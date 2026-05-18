import requests
import base64
import json
import wave
import struct
import math
import os

# Configuration
URL = "http://100.113.214.52:1234/v1/responses"
MODEL = "google/gemma-4-e4b"

def generate_test_wav(filename, duration_sec=0.2, freq=440.0):
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

def test_audio_responses():
    audio_path = "test_audio.wav"
    generate_test_wav(audio_path, duration_sec=0.1)
    audio_b64 = encode_file(audio_path)
    
    print(f"--- Testing Audio via /v1/responses (Embedded in String) ---")
    
    # We follow the pattern found in scripts/test_responses_base64_in_string.py
    payload = {
        "model": MODEL,
        "input": f"data:audio/wav;base64,{audio_b64}\n\nWhat is this sound? Please respond briefly."
    }
    
    try:
        response = requests.post(URL, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            res_json = response.json()
            # The /v1/responses endpoint likely returns a different structure than Chat Completions
            print("✅ Success!")
            print(json.dumps(res_json, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

if __name__ == "__main__":
    test_audio_responses()
