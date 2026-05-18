import requests
import base64
import json
import os
import time

URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"

# Data from logs/run_20260510_194221/agent_debug.log STEP 1
IMAGE_PATH = "logs/run_20260510_194221/step_1_before.png"
PROMPT = """你是一个 Android 自动化专家，正在驱动一台真实手机。
当前屏幕真实分辨率: 1080 x 2400 (所有坐标点 [x, y] 必须在此范围内)

【总目标】: 在地图搜索 'best pizza in San Francisco'，滚动寻找一家评分 >= 4.6 的店点进去，拿到电话号码，最后退回地图主页。
【已达成成就】: 无

【任务清单】（[x]=已完成 [→]=当前焦点 [ ]=待办）:
[→] 1. 当前在地图应用主页
[ ] 2. 已看到披萨搜索的结果列表
[ ] 3. 看到评分大于等于 4.6 的商家信息
[ ] 4. 屏幕上可见目标商家的电话号码
[ ] 5. 已成功返回地图主页界面
【当前焦点子任务】: 当前在地图应用主页

【scratchpad - 跨步记忆的事实信息】（0 条，可直接引用，例如发短信时引用电话号码）:
（暂无记录）

【上一步执行反馈】:
任务刚启动，尚未执行动作。当前可能在桌面、锁屏或任意 app，请先看截图判断是否需要 home/open_app 校正环境。

【本机已安装应用（open_app 时从中选 pkg）】:
com.aeva.mobile, com.android.camera2, com.android.chrome, com.android.settings, com.android.stk, com.google.android.apps.docs, com.google.android.apps.maps, com.google.android.apps.messaging, com.google.android.apps.photos, com.google.android.apps.youtube.music, com.google.android.calendar, com.google.android.contacts, com.google.android.deskclock, com.google.android.dialer, com.google.android.documentsui, com.google.android.gm, com.google.android.googlequicksearchbox, com.google.android.youtube, com.zhihu.android, io.appium.settings

【当前可交互清单】（注意：ID 仅本步有效，跨步引用请用 label 而非 ID）:
ID 0: ''Search conversations' id:searchbar (EditText)' @ [540, 212]
ID 1: 'desc:'More Options'' @ [116, 212]
ID 2: ''Search conversations' id:open_search_bar_text_view' @ [414, 212]
ID 3: 'desc:'Sign in' id:selected_account_disc' @ [964, 212]
ID 4: ''10086' id:conversation_name' @ [529, 381]
ID 5: ''You: Hello' id:conversation_snippet' @ [529, 444]
ID 6: ''6:29 PM' id:conversation_timestamp' @ [959, 372]
ID 7: ''12345' id:conversation_name' @ [550, 570]
ID 8: 'id:conversation_snippet' @ [550, 633]
ID 9: ''Draft' id:conversation_timestamp' @ [980, 561]
ID 10: ''Start chat' desc:'Start chat' id:start_chat_fab' @ [845, 2200]

【Gap 分析要求】：
1. 当前截图处于哪个 app / 页面？是否已经在目标 app？没有的话先 open_app。
2. 刚才那一步生效了吗？没生效的根因是什么？
3. 离总目标还差什么？**请对比【总目标】与【已达成成就】，严禁重复执行已完成的步骤。**
4. 如果目标已达成，请果断执行 "finish" 动作，不要因为页面细节微差而尝试重新开始。
5. 【兜底坐标点击】优先用 id；只有当目标元素（小图标、自定义 UI、Photos 选择器的 Done 等）在【当前可交互清单】中确实找不到时，才改用 `point: [x, y]` 直接给坐标。若用 point，请在 thought 中说明坐标是怎么估算的。

必须返回以下 JSON 格式（不要返回 markdown 包裹）:
{
  "thought": "按照分析要求来。必须给出动作理由，但禁止复述总目标全文。最后给出接下来的动作，以及为什么想这么做",
  "action": "click" | "type" | "scroll_down" | "scroll_up" | "back" | "home" | "open_app" | "long_press" | "wait" | "finish",
  "id": ID数字（仅 click/type/long_press 需要；清单里能找到就必填此字段而不是 point）,
  "point": [x, y]（仅当清单里找不到目标 ID 时备用，单位像素，必须在屏幕范围内）,
  "text": "输入内容（仅 type 需要）",
  "editor_action": "搜索/发送/完成等动作（仅 type 时可选）。可选值: 'search' | 'send' | 'done' | 'go' | 'next' | 'previous' | null。搜索框填 'search'，消息发送填 'send'，普通文本框填 null。比裸 Enter 键稳得多。",
  "pkg": "包名（仅 open_app 需要，必须是上面已安装清单里的）",
  "seconds": 3
}"""

def call_gemma(prompt, image_path):
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    system_msg = {"role": "system", "content": "You are a specialized Android automation robot. Do NOT think, do NOT reason, and do NOT output any preamble. Output ONLY the raw JSON structure."}
    user_content = [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
        {"type": "text", "text": prompt}
    ]

    payload = {
        "model": MODEL,
        "messages": [
            system_msg,
            {"role": "user", "content": user_content}
        ],
        "temperature": 0
    }

    start_time = time.time()
    try:
        response = requests.post(URL, json=payload, timeout=60)
        duration = time.time() - start_time
        res_json = response.json()
        content = res_json['choices'][0]['message'].get("content", "")
        usage = res_json.get("usage")
        return content, duration, usage
    except Exception as e:
        return f"Error: {e}", 0, None

if __name__ == "__main__":
    print(f"Testing with image: {IMAGE_PATH}")
    content, duration, usage = call_gemma(PROMPT, IMAGE_PATH)
    print(f"Response:\n{content}")
    print(f"\nDuration: {duration:.2f}s")
    print(f"Usage: {usage}")
