
import litert_lm
import os
import subprocess

# --- 配置区 ---
# 指向你本地 HF 缓存中的 Gemma-4 模型路径
MODEL_PATH = "/Users/a84513/.cache/huggingface/hub/models--litert-community--gemma-4-E4B-it-litert-lm/snapshots/10848a680ad0ab45b556566152371b38c238d6f0/gemma-4-E4B-it.litertlm"
# 你刚才录的那段“冠军语音”
AUDIO_PATH = "user_real_voice.wav"

def ensure_16k_wav(input_path):
    """确保音频是模型最爱的 16kHz 单声道 WAV"""
    output_path = "temp_16k_test.wav"
    print(f"[*] 正在转换音频格式: {input_path} -> {output_path}")
    # 使用 Mac 自带的 afconvert 进行转换
    cmd = [
        "afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
        input_path, output_path
    ]
    subprocess.run(cmd, check=True)
    return output_path

def run_gemma_audio_test():
    if not os.path.exists(MODEL_PATH):
        print(f"错误: 找不到模型文件 {MODEL_PATH}")
        return

    if not os.path.exists(AUDIO_PATH):
        print(f"错误: 找不到你的录音文件 {AUDIO_PATH}，请确保它在根目录")
        return

    # 1. 格式预处理
    target_audio = ensure_16k_wav(AUDIO_PATH)

    print(f"\n🚀 正在加载本地 Gemma-4 模型进行音频转录测试...")
    # 2. 初始化引擎 (使用 CPU 后端，因为在 Mac 上最稳)
    with litert_lm.Engine(MODEL_PATH, audio_backend=litert_lm.Backend.CPU) as engine:
        # 3. 创建对话 Session
        with engine.create_conversation() as conv:
            message = {
                "role": "user",
                "content": [
                    {"type": "audio", "path": os.path.abspath(target_audio)},
                    {"type": "text", "text": "这段录音里说了什么？请分别用中英文转录。"}
                ]
            }
            
            print("[*] 模型正在思考中...")
            # 4. 发送消息并获取响应
            response = conv.send_message(message)
            
            print("\n" + "="*30)
            print("✨ 模型响应结果:")
            print("="*30)
            
            # 解析响应内容
            if 'content' in response:
                for item in response['content']:
                    if item.get('type') == 'text':
                        print(item.get('text'))
            
            print("="*30 + "\n")

    # 清理临时文件
    if os.path.exists(target_audio):
        os.remove(target_audio)

if __name__ == "__main__":
    try:
        run_gemma_audio_test()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
