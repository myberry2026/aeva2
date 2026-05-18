
import requests
import base64
import os

# Ollama 默认地址
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
AUDIO_PATH = "user_real_voice.wav"

def get_audio_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def test_ollama_audio():
    if not os.path.exists(AUDIO_PATH):
        print(f"错误: 找不到音频 {AUDIO_PATH}")
        return

    audio_b64 = get_audio_base64(AUDIO_PATH)

    # 尝试将音频作为 image (blob) 发送
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "What is said in this audio? 请转录这段音频。",
                "images": [audio_b64]
            }
        ],
        "stream": False
    }

    print(f"\n🚀 正在尝试向 Local Ollama 发送音频请求 ({MODEL})...")
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        res_json = response.json()
        
        print("\n" + "="*30)
        print("✨ Ollama 响应结果:")
        print("="*30)
        print(res_json.get('message', {}).get('content', '无内容'))
        print("="*30 + "\n")
        
    except Exception as e:
        print(f"❌ Ollama 调用失败: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"错误详情: {e.response.text}")

if __name__ == "__main__":
    test_ollama_audio()
