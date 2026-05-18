import requests
import time
import json
import base64
import os
import re

def test_multimodal_openai():
    url = "http://localhost:11434/v1/chat/completions"
    model = "gemma4:26b"
    
    # 找一个现有的截图，如果没有就跳过图片测试
    img_path = "screenshots/step_1_before.png"
    if not os.path.exists(img_path):
        # 尝试找任何 png
        for f in os.listdir("screenshots"):
            if f.endswith(".png"):
                img_path = os.path.join("screenshots", f)
                break
    
    prompt = "请描述这张图片中的 Android 界面，并告诉我当前处于哪个 App。返回 JSON: {\"app\": \"\", \"description\": \"\"}"
    
    content = [{"type": "text", "text": prompt}]
    if os.path.exists(img_path):
        print(f"[*] 使用图片进行测试: {img_path}")
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"}
            })
    else:
        print("[!] 未找到截图，仅进行文本测试")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "stream": True,
        "temperature": 0.1
    }
    
    print(f"[*] 正在测试 OpenAI 兼容接口 (Vision): {model}")
    
    start_time = time.time()
    full_response = ""
    try:
        response = requests.post(url, json=payload, timeout=300, stream=True)
        
        print("\n[STREAMING RESPONSE]:")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8').replace('data: ', '')
                if decoded_line == '[DONE]': break
                try:
                    chunk = json.loads(decoded_line)
                    text = chunk['choices'][0]['delta'].get('content', '')
                    full_response += text
                    print(text, end="", flush=True)
                except: continue
        
        elapsed = time.time() - start_time
        print(f"\n\n[OK] 总耗时: {elapsed:.2f} 秒")
        
        match = re.search(r'\{.*\}', full_response, re.DOTALL)
        if match:
            print(f"\n[OK] 解析成功: {json.loads(match.group())}")
        else:
            print("\n[ERR] 未找到 JSON")
            
    except Exception as e:
        print(f"\n[ERR] 调用异常: {e}")

if __name__ == "__main__":
    test_multimodal_openai()
