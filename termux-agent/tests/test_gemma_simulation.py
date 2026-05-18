import requests
import time
import base64
import json

def test_full_simulation():
    import os
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    url = "http://localhost:11434/v1/chat/completions"
    
    list_path = os.path.join(BASE_DIR, "data", "inventory", "simulated_list_str.txt")
    with open(list_path, "r", encoding="utf-8") as f:
        list_str = f.read()
    
    img_path = os.path.join(BASE_DIR, "data", "screenshots", "step_1.png")
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    final_goal = "在知乎首页找到关于‘产检’的问题并进入详情页"
    done_str = "无"
    checklist = "[→] 1. 在知乎首页找到关于‘产检’的问题\n[ ] 2. 进入该问题详情页"
    focus_task = "在知乎首页找到关于‘产检’的问题"
    apps_str = "com.zhihu.android, com.android.chrome, com.google.android.apps.messaging"
    SCREEN_W, SCREEN_H = 1080, 2400

    prompt_decide = f"""
你是一个 Android 自动化专家，正在驱动一台真实手机。
当前屏幕真实分辨率: {SCREEN_W} x {SCREEN_H} (所有坐标点 [x, y] 必须在此范围内)

【总目标】: {final_goal}
【已达成成就】: {done_str}

【任务清单】（[x]=已完成 [→]=当前焦点 [ ]=待办）:
{checklist}
【当前焦点子任务】: {focus_task}

【上一步执行反馈】:
首次启动，请开始任务。

【本机已安装应用（open_app 时从中选 pkg）】:
{apps_str}

【当前可交互清单】（注意：ID 仅本步有效，跨步引用请用 label 而非 ID）:
{list_str}

【Gap 分析要求】：
1. 当前截图处于哪个 app / 页面？是否已经在目标 app？没有的话先 open_app。
2. 刚才那一步生效了吗？没生效的根因是什么？
3. 离总目标还差什么？**请对比【总目标】与【已达成成就】，严禁重复执行已完成的步骤。**
4. 如果目标已达成，请果断执行 "finish" 动作，不要因为页面细节微差而尝试重新开始。
5. 【兜底坐标点击】优先用 id；只有当目标元素（小图标、自定义 UI、Photos 选择器的 Done 等）在【当前可交互清单】中确实找不到时，才改用 `point: [x, y]` 直接给坐标。若用 point，请在 thought 中说明坐标是怎么估算的。

必须返回以下 JSON 格式（不要返回 markdown 包裹）:
{{
  "thought": "按照分析要求来。必须给出动作理由，但禁止复述总目标全文。最后给出接下来的动作，以及为什么想这么做",
  "action": "click" | "type" | "scroll_down" | "scroll_up" | "back" | "home" | "open_app" | "long_press" | "wait" | "finish",
  "id": ID数字（仅 click/type/long_press 需要；清单里能找到就必填此字段而不是 point）,
  "point": [x, y]（仅当清单里找不到目标 ID 时备用，单位像素，必须在屏幕范围内）,
  "text": "输入内容（仅 type 需要）",
  "pkg": "包名（仅 open_app 需要，必须是上面已安装清单里的）",
  "seconds": 3
}}
"""
    
    system_msg = {"role": "system", "content": "You are a specialized Android automation robot. Do NOT think, do NOT reason, and do NOT output any preamble. Output ONLY the raw JSON structure."}
    user_content = [
        {"type": "text", "text": prompt_decide},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
    ]

    payload = {
        "model": "gemma4:latest",
        "messages": [
            system_msg,
            {"role": "user", "content": user_content}
        ],
        "temperature": 1.0,
        "top_p": 0.95
    }

    print(f"[*] Sending Full Simulation Request to Gemma-4...")
    start_time = time.time()
    response = requests.post(url, json=payload)
    end_time = time.time()
    
    res_text = response.json()['choices'][0]['message'].get("content", "")
    
    print(f"\n{'='*40}")
    print(f"Time Taken: {end_time - start_time:.2f} seconds")
    print(f"Model Response:\n{res_text}")
    print(f"{'='*40}")

if __name__ == "__main__":
    test_full_simulation()
