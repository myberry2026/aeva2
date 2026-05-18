import requests
import json
import base64
import os

def test_new_model():
    # 使用用户提供的配置
    base_url = "http://100.113.214.52:1234/v1"
    model = "google/gemma-4-e4b"
    url = f"{base_url}/chat/completions" # 尝试标准路径
    
    print(f"Testing URL: {url}")
    print(f"Testing Model: {model}")

    # 准备一个简单的带图片的 prompt
    # 找一个现有的截图
    img_path = None
    if os.path.exists("test.png"):
        img_path = "test.png"
    else:
        # 找找是否有其他 png
        for f in os.listdir("."):
            if f.endswith(".png"):
                img_path = f
                break
    
    if not img_path:
        print("No image found for testing vision.")
        # 测试纯文本
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Hello, who are you? Please respond in JSON format like {'name': '...'}."}
            ],
            "stream": False
        }
    else:
        print(f"Using image: {img_path}")
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What do you see in this image? Respond in JSON format: {'description': '...'}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    ]
                }
            ],
            "stream": False
        }

    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"Error: {response.text}")
            
            # 如果 /chat/completions 不通，尝试 /responses (用户 curl 里提到的)
            url_alt = f"{base_url}/responses"
            print(f"Trying alternative URL: {url_alt}")
            # 注意: /responses 可能不是标准的 chat/completions 格式，可能需要调整 payload
            # 这里先原样尝试
            response_alt = requests.post(url_alt, json=payload, timeout=30)
            print(f"Alt Status Code: {response_alt.status_code}")
            if response_alt.status_code == 200:
                print("Alt Success!")
                print(json.dumps(response_alt.json(), indent=2, ensure_ascii=False))
            else:
                print(f"Alt Error: {response_alt.text}")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_new_model()
