import os
import requests
import base64
import json
import time
from device_controller import ADBController

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e2b"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def agent_live_step():
    device = ADBController()
    print("[*] 📸 正在抓取模拟器当前状态 (Screenshot + XML)...")
    
    # 1. 准备素材
    img_path = "profiling/live_state.png"
    os.system(f"adb shell screencap -p /sdcard/live.png && adb pull /sdcard/live.png {img_path}")
    inventory = device.get_inventory()
    
    # 2. 构建给模型的 Prompt
    inventory_str = "\n".join([f"ID {e['id']}: '{e['label']}' @ {e['pos']}" for e in inventory])
    
    user_content = [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image(img_path)}"}},
        {"type": "text", "text": f"""Current UI Inventory:
{inventory_str}

Goal: Search for 'best pizza in San Francisco' in Google Maps.

Based on the XML tree above, exactly which ID should I click to start typing the search query? 
Please provide the action in JSON format like: 
{{"thought": "...", "action": {{"type": "tap", "id": 123, "text": "..."}}}}
"""}
    ]

    print(f"[*] 🧠 正在请求模型进行实时分析...")
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": 512,
        "extra_body": { "num_ctx": 32000 }
    }

    resp = requests.post(URL, json=payload, timeout=60)
    if resp.status_code == 200:
        res = resp.json()['choices'][0]['message'].get('content')
        print("\n" + "="*20 + " 模型实时决策 " + "="*20)
        print(res)
        
        # 尝试解析并执行
        try:
            import re
            action_match = re.search(r'\{.*\}', res, re.DOTALL)
            if action_match:
                decision = json.loads(action_match.group())
                target_id = decision['action']['id']
                target_node = next((e for e in inventory if e['id'] == target_id), None)
                if target_node:
                    print(f"[*] 执行动作: 点击 ID {target_id} ({target_node['label']})")
                    device.tap(*target_node['pos'])
                    time.sleep(2)
                    device.type("best pizza in San Francisco", editor_action="search")
                    print("[*] ✅ 动作执行完毕，请看结果。")
        except Exception as e:
            print(f"[!] 解析或执行失败: {e}")
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    agent_live_step()
