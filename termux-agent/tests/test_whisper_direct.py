import requests
import base64
import json
import wave
import struct
import math
import os
import time

# Configuration
URL = "http://100.113.214.52:1234/v1/audio/transcriptions"
MODEL = "whisper-large-v3-turbo"

def generate_speech_like(filename, duration_sec=1.0):
    sample_rate = 16000
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        # Just random noise to see if it even accepts the file
        for _ in range(int(sample_rate * duration_sec)):
            value = 0 # Silent
            wav_file.writeframesraw(struct.pack('<h', value))
    print(f"[*] Generated silent audio: {filename}")

def test_whisper():
    filename = "test_whisper.wav"
    generate_speech_like(filename)
    
    print(f"\n--- Testing Whisper Model ({MODEL}) via /v1/audio/transcriptions ---")
    
    try:
        with open(filename, "rb") as f:
            # Note: Many proxies for Whisper expect multipart/form-data
            files = {
                "file": (filename, f, "audio/wav")
            }
            data = {
                "model": MODEL,
                "language": "en"
            }
            # Try to send with proper headers
            response = requests.post(URL, files=files, data=data, timeout=30)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_whisper()
