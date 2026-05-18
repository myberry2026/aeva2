import requests
import base64
import json
import wave
import struct
import math
import os

# 配置
URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

def generate_test_wav(filename, duration_sec=0.1, freq=440.0):
    """
    生成一个简单的正弦波 WAV 文件。
    注意：Gemma-4 E4B 建议采样率为 16kHz。
    """
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            # 生成 A4 (440Hz) 音调
            value = int(32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)
    print(f"[*] 已生成测试音频: {filename} ({duration_sec}s, {sample_rate}Hz)")

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_audio_support():
    audio_path = "test_audio.wav"
    generate_test_wav(audio_path)
    audio_b64 = encode_file(audio_path)
    
    print(f"\n--- 测试模型音频支持 ({MODEL}) ---")
    
    # 核心发现：在当前 Proxy 下，必须将 Data URI 嵌入到 text 字符串中才能触发音频解析。
    # 如果使用 OpenAI 标准的 type: "input_audio"，会被 Proxy 拦截。
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"data:audio/wav;base64,{audio_b64}\n\n这是一段音频。请告诉我你听到了什么？只需简短描述。"
            }
        ],
        "temperature": 0
    }
    
    try:
        print("[*] 正在发送请求...")
        response = requests.post(URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            res_json = response.json()
            content = res_json['choices'][0]['message'].get("content", "")
            print("✅ 模型响应成功！")
            print("-" * 30)
            print(f"AI 回复: {content}")
            print("-" * 30)
            
            # 打印 Token 用量
            usage = res_json.get("usage", {})
            print(f"Token 用量: {usage}")
        else:
            print(f"❌ 请求失败 (Status {response.status_code})")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 发生异常: {e}")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

if __name__ == "__main__":
    test_audio_support()
