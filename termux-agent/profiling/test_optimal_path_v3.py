import time
import os
from device_controller import BridgeController, ADBController

# 配置环境
BACKEND = "adb"

def get_device():
    return ADBController()

def test_optimal_path_v3():
    device = get_device()
    pkg = "com.google.android.apps.messaging"
    target_contact = "10086"
    msg_text = "Hello (Optimal Path V3)"

    print(f"[*] 🚀 启动最优路径测试 V3 (后端: {BACKEND})")

    # 1. 启动并进入短信
    device.open_app(pkg)
    time.sleep(5) # 启动给足时间

    # 2. 检查环境
    elements = device.get_inventory()
    print(f"[*] 当前屏幕控件数: {len(elements)}")
    for e in elements:
        print(f"    - [{e['id']}] {e['label']} @ {e['pos']}")

    in_thread = any(target_contact in e['label'] for e in elements if "conversation_title" in e['label'])
    
    if not in_thread:
        print(f"[*] 没在对话里，开始找搜索入口...")
        search_btn = next((e for e in elements if "start_chat" in e['label'].lower() or "search" in e['label'].lower()), None)
        if search_btn:
            print(f"[*] 点击搜索按钮: {search_btn['label']}")
            device.tap(*search_btn['pos'])
            time.sleep(2)
            print(f"[*] 盲打搜索内容: {target_contact}")
            device.tap_and_type(500, 200, target_contact, editor_action="send") # 尝试在中间偏上点一下再打字
            time.sleep(5) # 给搜索结果留时间
            
            # 重新扫描
            elements = device.get_inventory()
            print(f"[*] 搜索后控件数: {len(elements)}")
            for e in elements:
                if target_contact in e['label']:
                    print(f"[*] 发现搜索结果: {e['label']}，点击进入...")
                    device.tap(*e['pos'])
                    time.sleep(3)
                    break
    
    # 3. 最终确认并发送
    elements = device.get_inventory()
    input_box = next((e for e in elements if "compose_message_text" in e['label']), None)
    
    if input_box:
        print(f"[*] 找到输入框! 执行一键发送...")
        device.tap_and_type(input_box['pos'][0], input_box['pos'][1], msg_text, editor_action="send")
        print("[*] DONE.")
    else:
        print("[!] 依旧没找到输入框。我太难了。")

if __name__ == "__main__":
    test_optimal_path_v3()
