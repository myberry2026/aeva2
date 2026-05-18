import time
import os
from device_controller import BridgeController, ADBController

# 配置环境
BACKEND = "adb"

def get_device():
    return ADBController()

def test_optimal_path_v4():
    device = get_device()
    pkg = "com.google.android.apps.messaging"
    target_contact = "10086"
    msg_text = "Hello (Optimal Path V4)"

    print(f"[*] 🚀 启动最优路径测试 V4 (后端: {BACKEND})")

    # 1. 启动
    device.open_app(pkg)
    time.sleep(5)

    # 2. 检查环境
    elements = device.get_inventory()
    
    # 策略 A：是否已经在对话里？
    in_thread = any(target_contact in e['label'] and "conversation_title" in e['label'] for e in elements)
    
    if in_thread:
        print("[*] 已经在对话中了。")
    else:
        # 策略 B：是否在列表中能看到？
        list_item = next((e for e in elements if target_contact in e['label'] and "conversation_name" in e['label']), None)
        if list_item:
            print(f"[*] 在首页列表发现 {target_contact}，直接点击进入...")
            device.tap(*list_item['pos'])
            time.sleep(3)
        else:
            # 策略 C：搜索（兜底）
            print("[*] 列表中没看到，尝试搜索...")
            search_btn = next((e for e in elements if "search" in e['label'].lower()), None)
            if search_btn:
                device.tap(*search_btn['pos'])
                time.sleep(2)
                device.tap_and_type(500, 200, target_contact, editor_action="send")
                time.sleep(5)
                elements = device.get_inventory()
                item = next((e for e in elements if target_contact in e['label']), None)
                if item: device.tap(*item['pos']); time.sleep(3)

    # 3. 定位输入框并一键发送
    elements = device.get_inventory()
    input_box = next((e for e in elements if "compose_message_text" in e['label']), None)
    
    if input_box:
        print(f"[*] 找到输入框! 执行最优动作: type('{msg_text}', editor_action='send')")
        device.tap_and_type(input_box['pos'][0], input_box['pos'][1], msg_text, editor_action="send")
        print("[*] ✅ 动作成功发出。")
        time.sleep(2)
        # 验证
        elements = device.get_inventory()
        if any("SMS" in e['label'] or "message_status" in e['label'] for e in elements):
            print("\n" + "🎊"*10)
            print("🎊 最优路径实测大获全胜！")
            print("🎊"*10 + "\n")
    else:
        print("[!] 依旧没找到输入框。")

if __name__ == "__main__":
    test_optimal_path_v4()
