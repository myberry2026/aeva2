import subprocess
import time
import base64
import json
import requests
import os

def log(msg):
    print(f"[*] {msg}")

def open_apps_on_emulator():
    # 尝试打开计算器和设置
    apps = [
        "com.android.calculator2", 
        "com.android.settings"
    ]
    for app in apps:
        log(f"正在模拟器中打开应用: {app}...")
        # 使用 monkey 命令尝试拉起主 Activity
        subprocess.run(["adb", "shell", "monkey", "-p", app, "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
    time.sleep(5)

def take_emulator_screenshot(output_path):
    log(f"正在截取模拟器屏幕: {output_path}...")
    try:
        with open(output_path, "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f, check=True)
        return output_path
    except Exception as e:
        log(f"截图失败: {e}")
        return None

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def query_ollama(model, prompt, image_base64):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_base64],
        "stream": False
    }
    
    log(f"正在向 Ollama ({model}) 发送请求...")
    start_time = time.time()
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        duration = time.time() - start_time
        log(f"请求完成，耗时 {duration:.2f} 秒")
        return response.json().get("response", "")
    except Exception as e:
        log(f"请求失败: {e}")
        return None

def main():
    screenshot_file = "emulator_vision_test.png"
    model_name = "gemma4:latest"
    
    # 1. 打开应用
    open_apps_on_emulator()
    
    # 2. 截图
    if not take_emulator_screenshot(screenshot_file):
        return
    
    # 3. 编码图片
    img_b64 = encode_image(screenshot_file)
    
    # 4. 询问 AI
    prompt = "在这张手机截图中，你看到了哪些正在运行的应用程序？请列出它们的名字并简要描述屏幕内容。"
    result = query_ollama(model_name, prompt, img_b64)
    
    if result:
        print("\n" + "="*50)
        print(f"AI ({model_name}) 的识别结果:")
        print("-" * 50)
        print(result)
        print("="*50 + "\n")
    else:
        log("未能从 AI 获取结果。")

if __name__ == "__main__":
    main()
