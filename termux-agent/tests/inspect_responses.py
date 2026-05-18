import requests
import base64
import json
import os

URL = "http://100.113.214.52:1234/v1/responses"
AUDIO_FILE = "test_audio_chat.wav"

if not os.path.exists(AUDIO_FILE):
    # Generate a fallback beep if file is missing (though we saw it earlier)
    print(f"Warning: {AUDIO_FILE} not found, generating temporary beep.")
    import wave, struct, math
    with wave.open(AUDIO_FILE, 'w') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000)
        for i in range(1600):
            val = int(32767.0 * math.sin(2.0 * math.pi * 440.0 * i / 16000))
            f.writeframesraw(struct.pack('<h', val))

audio_b64 = base64.b64encode(open(AUDIO_FILE, "rb").read()).decode('utf-8')
payload = {
    "model": "google/gemma-4-e4b",
    "input": f"data:audio/wav;base64,{audio_b64}\n\nWhat is in this audio? Answer in one sentence."
}

print(f"[*] Sending request to {URL}...")
r = requests.post(URL, json=payload, timeout=60)
data = r.json()

# Save to file in current directory
with open("response_inspect.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"[*] Response saved to response_inspect.json")

# Try to find content
try:
    # Let's be very safe with nested lookups
    if 'output' in data:
        output = data['output']
        if isinstance(output, list):
            content = output[0].get('text', {}).get('content', 'MISSING_CONTENT')
        elif isinstance(output, dict):
            # Try choices style
            choices = output.get('choices', [])
            if choices:
                content = choices[0].get('message', {}).get('content', 'MISSING_CONTENT')
            else:
                content = output.get('text', {}).get('content', 'MISSING_CONTENT')
    else:
        content = data.get('choices', [{}])[0].get('message', {}).get('content', 'MISSING_CONTENT')
    
    print(f"[*] Extracted Content: {content}")
except Exception as e:
    print(f"[*] Failed to extract content: {e}")
    print(f"[*] Raw keys: {data.keys()}")
