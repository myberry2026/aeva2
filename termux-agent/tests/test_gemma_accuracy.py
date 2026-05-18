import requests
import time
import json

def test_gemma_coords():
    url = "http://localhost:11434/v1/chat/completions"
    
    # 构造一个模拟 UI 上下文的 Prompt
    # 模拟 agent 在决策时的输入
    prompt = """
    Current Screen Context (Simplified UI Tree):
    - [0, 128, 1080, 2337] FrameLayout
      - [0, 128, 1080, 282] TabLayout
        - [36, 128, 204, 282] Tab: "关注"
        - [204, 128, 372, 282] Tab: "推荐"
        - [372, 128, 537, 282] Tab: "热榜"
        - [537, 128, 705, 282] Tab: "故事"
    
    Goal: Click on the "热榜" tab.
    Question: What are the center coordinates (x, y) of the "热榜" tab? 
    Please respond ONLY with the coordinates in format: [x, y].
    """

    payload = {
        "model": "gemma4:latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }

    print(f"[*] Sending request to Gemma-4 via Ollama...")
    start_time = time.time()
    
    response = requests.post(url, json=payload)
    end_time = time.time()
    
    res_json = response.json()
    answer = res_json['choices'][0]['message']['content'].strip()
    
    print(f"\n{'='*40}")
    print(f"Model Response: {answer}")
    print(f"Time Taken: {end_time - start_time:.2f} seconds")
    print(f"Ground Truth: [454, 205]")
    print(f"{'='*40}")

if __name__ == "__main__":
    test_gemma_coords()
