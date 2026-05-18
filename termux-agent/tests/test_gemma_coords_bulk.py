import requests
import time
import json
import math

# Ground Truth Data
TEST_CASES = [
    {"name": "推荐 (Tab)", "target": "推荐", "bounds": [174, 148, 264, 214]},
    {"name": "有必要做产检吗? (Title)", "target": "有必要做产检吗?", "bounds": [42, 523, 371, 591]},
    {"name": "惜字人 (Author)", "target": "惜字人", "bounds": [110, 607, 218, 662]},
    {"name": "一键登录 (Button)", "target": "一键登录", "bounds": [845, 2082, 1024, 2150]},
    {"name": "首页 (Bottom Nav)", "target": "首页", "bounds": [82, 2277, 134, 2314]}
]

UI_CONTEXT = """
Simplified UI Hierarchy:
- [0, 0, 1080, 2400] Root
  - [0, 128, 1080, 282] HeaderTabs
    - [36, 128, 174, 282] "关注"
    - [174, 148, 264, 214] "推荐"
    - [372, 128, 537, 282] "热榜"
  - [0, 480, 1080, 1500] ContentList
    - [42, 523, 371, 591] "有必要做产检吗?"
    - [110, 607, 218, 662] "惜字人"
  - [0, 2000, 1080, 2200] LoginBanner
    - [845, 2082, 1024, 2150] "一键登录"
  - [0, 2250, 1080, 2337] BottomNav
    - [82, 2277, 134, 2314] "首页"
"""

def call_gemma(target_text):
    url = "http://localhost:11434/v1/chat/completions"
    prompt = f"""
    {UI_CONTEXT}
    
    Task: Find the center coordinates (x, y) for the element: "{target_text}"
    Respond ONLY with the coordinates in the format: [x, y]
    """
    
    payload = {
        "model": "gemma4:latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=30)
        duration = time.time() - start_time
        res_json = response.json()
        content = res_json['choices'][0]['message']['content'].strip()
        return content, duration
    except Exception as e:
        return f"Error: {e}", 0

def calculate_error(pred_str, bounds):
    try:
        # Parse [x, y]
        pred_str = pred_str.replace("[", "").replace("]", "").split(",")
        px, py = float(pred_str[0]), float(pred_str[1])
        
        tx = (bounds[0] + bounds[2]) / 2
        ty = (bounds[1] + bounds[3]) / 2
        
        distance = math.sqrt((px - tx)**2 + (py - ty)**2)
        return distance, (tx, ty), (px, py)
    except:
        return None, None, None

def run_tests():
    print(f"{'Name':<25} | {'Status':<10} | {'Error (px)':<10} | {'Time (s)':<8}")
    print("-" * 65)
    
    total_error = 0
    count = 0
    
    for case in TEST_CASES:
        ans, duration = call_gemma(case['target'])
        dist, truth, pred = calculate_error(ans, case['bounds'])
        
        status = "FAIL" if dist is None or dist > 50 else "PASS"
        err_str = f"{dist:.2f}" if dist is not None else "N/A"
        
        print(f"{case['name']:<25} | {status:<10} | {err_str:<10} | {duration:.2f}")
        
        if dist is not None:
            total_error += dist
            count += 1
            
    if count > 0:
        print("-" * 65)
        print(f"Average Error: {total_error/count:.2f} px")

if __name__ == "__main__":
    run_tests()
