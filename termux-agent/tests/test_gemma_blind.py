import requests
import time
import math

# 从本地读取原始的、杂乱的 XML 
with open("test_context.xml", "r", encoding="utf-8") as f:
    RAW_XML_CHUNK = f.read()

# 目标：找一个稍微靠后、没那么显眼的元素
TARGET = "有必要做产检吗?"
# 真实坐标：[42,523][371,591] -> 中心点 [206.5, 557]

def test_gemma_real_blind():
    url = "http://localhost:11434/v1/chat/completions"
    
    # 这里的 Prompt 不再包含任何 [x1, y1, x2, y2] 的提示，只给原始 XML 块
    prompt = f"""
    Below is a raw XML snippet from an Android UI dump. 
    Find the element with text="{TARGET}". 
    Extract its 'bounds' attribute, and calculate its center coordinates (x, y).
    
    RAW XML:
    {RAW_XML_CHUNK}
    
    Respond ONLY with the center coordinates in format: [x, y].
    """

    payload = {
        "model": "gemma4:latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }

    print(f"[*] Sending RAW XML to Gemma-4 (Blind Test)...")
    start_time = time.time()
    response = requests.post(url, json=payload)
    end_time = time.time()
    
    answer = response.json()['choices'][0]['message']['content'].strip()
    
    print(f"\n{'='*40}")
    print(f"Target Element: {TARGET}")
    print(f"Model Response: {answer}")
    print(f"Time Taken: {end_time - start_time:.2f} seconds")
    print(f"Ground Truth: [206.5, 557]")
    print(f"{'='*40}")

if __name__ == "__main__":
    test_gemma_real_blind()
