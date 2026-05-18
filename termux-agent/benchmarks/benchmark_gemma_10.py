import requests
import time
import base64
import json
import os

# Base directory for data files
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
IMG_DIR = os.path.join(BASE_DIR, "data", "screenshots")
INV_DIR = os.path.join(BASE_DIR, "data", "inventory")

def call_gemma(prompt, img_path):
    url = "http://localhost:11434/v1/chat/completions"
    try:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        return f"Error reading image: {e}", 0, None

    system_msg = {"role": "system", "content": "You are a specialized Android automation robot. Output ONLY raw JSON."}
    user_content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
    ]

    payload = {
        "model": "gemma4:latest",
        "messages": [system_msg, {"role": "user", "content": user_content}],
        "temperature": 0
    }

    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=60)
        duration = time.time() - start_time
        res_json = response.json()
        content = res_json['choices'][0]['message'].get("content", "")
        usage = res_json.get("usage")
        return content, duration, usage
    except Exception as e:
        return f"Error: {e}", 0, None

def run_benchmark():
    scenarios = [
        {"name": "Zhihu: Hot List", "img": "step_1.png", "goal": "切换到‘热榜’标签页", "expected_id": 5, "list": "step_1_list.txt"},
        {"name": "Zhihu: Pregnancy Quest", "img": "step_1.png", "goal": "点击查看‘有必要做产检吗?’这个提问", "expected_id": 25, "list": "step_1_list.txt"},
        {"name": "Zhihu: Author Profile 1", "img": "step_2.png", "goal": "进入作者‘不爱虚名爱恶名’的主页", "expected_id": 26, "list": "step_2_list.txt"},
        {"name": "Zhihu: Vance News", "img": "step_2.png", "goal": "阅读关于‘美国副总统万斯’的文章", "expected_id": 37, "list": "step_2_list.txt"},
        {"name": "Zhihu: Author Profile 2", "img": "step_3.png", "goal": "查看作者‘Curry’发表的内容", "expected_id": 28, "list": "step_3_list.txt"},
        {"name": "Zhihu: iPhone Security", "img": "step_3.png", "goal": "进入‘iPhone真的安全吗’问题的详情页", "expected_id": 38, "list": "step_3_list.txt"},
        {"name": "Zhihu: Recommend Tab", "img": "step_4.png", "goal": "点击‘推荐’标签返回首页推荐", "expected_id": 3, "list": "step_4_list.txt"},
        {"name": "Zhihu: Following Tab", "img": "step_4.png", "goal": "切换到‘关注’标签查看动态", "expected_id": 1, "list": "step_4_list.txt"},
        {"name": "Zhihu: One-click Login", "img": "step_5.png", "goal": "点击‘一键登录’按钮", "expected_id": 43, "list": "step_5_list.txt"},
        {"name": "Zhihu: Direct Answer", "img": "step_5.png", "goal": "点击底部导航栏的‘直答’", "expected_id": 48, "list": "step_5_list.txt"},
    ]

    print(f"{'Scenario':<25} | {'Status':<6} | {'Pred':<4} | {'Time(s)':<8} | {'Tokens(I/O)':<12}")
    print("-" * 75)

    for s in scenarios:
        img_path = os.path.join(IMG_DIR, s['img'])
        list_path = os.path.join(INV_DIR, s['list'])
        
        try:
            with open(list_path, "r") as f:
                list_str = f.read()
        except Exception as e:
            print(f"Error reading {list_path}: {e}")
            continue
        
        prompt = f"""
        Current Screen Context:
        Goal: {s['goal']}
        Interactive Elements:
        {list_str}
        
        Analyze screenshot and list. Identify the BEST element ID. 
        Return ONLY JSON: {{"thought": "...", "action": "click", "id": ID}}
        """
        
        ans, duration, usage = call_gemma(prompt, img_path)
        pred_id = -1
        try:
            # Simple regex to find JSON
            import re
            match_json = re.search(r'\{.*\}', ans, re.DOTALL)
            if match_json:
                data = json.loads(match_json.group())
                pred_id = data.get("id")
        except: pass
        
        usage_str = f"{usage.get('prompt_tokens','?')}/{usage.get('completion_tokens','?')}" if usage else "N/A"
        status = "PASS" if pred_id == s['expected_id'] else "FAIL"
        print(f"{s['name']:<25} | {status:<6} | {str(pred_id):<4} | {duration:.2f}     | {usage_str:<12}")

if __name__ == "__main__":
    run_benchmark()
