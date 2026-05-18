
import requests
import base64
import os
import subprocess

# --- Endpoint 配置 ---
URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"
AUDIO_PATH = "user_real_voice.wav"

def get_audio_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def ensure_16k_wav(input_path):
    output_path = "temp_endpoint_test.wav"
    print(f"[*] 格式预处理: {input_path} -> {output_path}")
    subprocess.run([
        "afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
        input_path, output_path
    ], check=True)
    return output_path

def test_endpoint_audio():
    if not os.path.exists(AUDIO_PATH):
        print(f"错误: 找不到音频 {AUDIO_PATH}")
        return

    # 1. 预处理音频
    processed_audio = ensure_16k_wav(AUDIO_PATH)
    audio_b64 = get_audio_base64(processed_audio)

    # 2. 构造 OpenAI 兼容的消息格式
    # 注意：很多端侧服务器对 content 列表中的 audio 类型有特定要求
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": "Please transcribe the audio attached. 这一段录音里说了什么？"
                    },
                    {
                        "type": "audio",
                        "audio": {
                            "data": audio_b64,
                            "format": "wav"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.0
    }

    print(f"\n🚀 正在向 Endpoint 发送音频请求 ({URL})...")
    try:
        response = requests.post(URL, json=payload, timeout=60)
        response.raise_for_status()
        res_json = response.json()
        
        print("\n" + "="*30)
        print("✨ Endpoint 响应结果:")
        print("="*30)
        content = res_json['choices'][0]['message']['content']
        print(content)
        print("="*30 + "\n")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Endpoint 调用失败 (HTTP {e.response.status_code}): {e.response.text}")
    except Exception as e:
        print(f"❌ 发生其他错误: {e}")

    # 清理
    if os.path.exists(processed_audio):
        os.remove(processed_audio)

if __name__ == "__main__":
    test_endpoint_audio()
