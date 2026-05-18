import requests
import json
import time
import base64
import os

def test_remote_model():
    # 用户提供的配置
    base_url = "http://100.113.214.52:1234/v1"
    url = f"{base_url}/chat/completions"
    model = "google/gemma-4-e4b"
    
    print(f"[*] 正在测试远程模型: {model}")
    print(f"[*] 目标 URL: {url}")

    # 准备一张测试图片
    img_path = "screenshots/step_1_before.png"
    if not os.path.exists(img_path):
        # 尝试找任何 png
        for f in os.listdir("screenshots"):
            if f.endswith(".png"):
                img_path = os.path.join("screenshots", f)
                break

    prompt = "你现在是一个 Android 专家。请告诉我这张图里当前打开的是什么 App？返回 JSON: {\"app\": \"\"}"
    
    content = [{"type": "text", "text": prompt}]
    if os.path.exists(img_path):
        print(f"[*] 携带图片测试: {img_path}")
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"}
            })
    else:
        print("[!] 未找到截图，执行纯文本测试")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "stream": False
    }

    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=60)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            res_json = response.json()
            answer = res_json['choices'][0]['message'].get('content', '')
            print(f"\n[OK] 耗时: {elapsed:.2f} 秒")
            print(f"[OK] 模型响应内容:\n{answer}")
        else:
            print(f"\n[ERR] HTTP 状态码: {response.status_code}")
            print(f"响应原文: {response.text}")
            
    except Exception as e:
        print(f"\n[ERR] 调用发生异常: {e}")

if __name__ == "__main__":
    test_remote_model()
