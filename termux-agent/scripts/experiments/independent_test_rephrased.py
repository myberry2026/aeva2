import requests
import base64
import json
import os
import time
import sys

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"
IMG1 = "logs/run_20260510_194221/step_1_before.png"
IMG2 = "logs/run_20260510_194221/step_1_after.png"

def call_remote(prompt, image_paths=[]):
    user_content = []
    for path in image_paths:
        with open(path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })
    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a specialized Android automation robot. Respond strictly in JSON."},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0
    }

    start_time = time.time()
    try:
        with requests.Session() as session:
            response = session.post(URL, json=payload, timeout=120)
            duration = time.time() - start_time
            res_json = response.json()
            usage = res_json.get("usage")
            return duration, usage
    except Exception as e:
        return 0, {"error": str(e)}

# Three completely different ways to express the same long prompt
PROMPTS = [
    # Version 1: Standard
    """你现在是一名精通 Android 自动化操作的专家。你的任务是操作这台手机。
    目标：在地图里搜旧金山最好的披萨，找个 4.6 分以上的店，点进去拿电话，最后回主页。
    当前已经完成：无。
    待办清单：1. 在地图主页；2. 看到搜索结果；3. 看到 4.6 分以上的店；4. 看到电话；5. 回到主页。
    可交互元素如下：
    ID 0: 'Search conversations' @ [540, 212]
    ID 1: 'More Options' @ [116, 212]
    ID 10: 'Start chat' @ [845, 2200]
    请分析当前 Gap 并给出下一步动作 JSON。""",

    # Version 2: Rephrased & Formal
    """作为 Android 视觉自动化智能体，请执行以下指令流。
    任务终点：获取旧金山评分高于 4.6 的披萨店联系电话并归位。
    状态跟踪：目前任务刚启动。
    后续阶段：[地图主页] -> [列表展示] -> [高分筛选] -> [详情查看] -> [退出程序]。
    当前 UI 树摘要：
    ID 0: 输入框 (EditText) 坐标 [540, 212]
    ID 1: 更多选项按钮 坐标 [116, 212]
    ID 10: 发起聊天悬浮按钮 坐标 [845, 2200]
    请基于视觉反馈与清单，返回 action, id/point, thought 构成的 JSON。""",

    # Version 3: Restructured & Direct
    """【指令集】操作 Android 设备。
    【核心目标】搜索 'best pizza in San Francisco' -> 筛选 >= 4.6 分 -> 获取电话 -> 回主页。
    【进度表】
    - 地图主页：待达成
    - 结果展示：待达成
    - 电话可见：待达成
    【元素表】
    ID 0 (Search conversations), ID 1 (More Options), ID 10 (Start chat fab).
    【要求】对比截图与清单，找出差异，执行 open_app 或其他动作。
    输出格式要求：RAW JSON。"""
]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python independent_test_rephrased.py [0|1|2]")
        sys.exit(1)
    
    idx = int(sys.argv[1])
    p = PROMPTS[idx]
    imgs = [IMG1, IMG2][:idx] # 0 imgs for idx 0, 1 for 1, 2 for 2
    
    print(f"[*] Running Case {idx} (Images: {idx}) with unique text...")
    duration, usage = call_remote(p, imgs)
    
    result = {
        "case": f"{idx} Images",
        "duration": f"{duration:.2f}s",
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens")
    }
    print(json.dumps(result, indent=2))
