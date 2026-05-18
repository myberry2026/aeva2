import time
import os
from device_controller import BridgeController, ADBController

# 配置环境
BACKEND = "adb" # 暂时用 adb 绕过 401

def get_device():
    if BACKEND == "bridge":
        return BridgeController(os.getenv("BRIDGE_URL", "http://127.0.0.1:8765"), "")
    return ADBController()

def test_optimal_path_v2():
    device = get_device()
    pkg = "com.google.android.apps.messaging"
    target_contact = "10086"
    msg_text = "Hello (Optimal Path Test)"

    print(f"[*] 🚀 启动最优路径测试 V2 (后端: {BACKEND})")

    # 1. 启动并进入短信
    device.open_app(pkg)
    time.sleep(3)

    # 2. 检查是否在目标会话，不在就搜索
    elements = device.get_inventory()
    in_thread = any(target_contact in e['label'] for e in elements if e['id'] == "conversation_title")
    
    if not in_thread:
        print(f"[*] 不在 {target_contact} 对话中，执行搜索进入...")
        # 寻找搜索图标或新对话按钮 (通常是 start_chat_fab)
        search_btn = next((e for e in elements if "start_chat" in e['label'].lower() or "search" in e['label'].lower()), None)
        if search_btn:
            device.tap(*search_btn['pos'])
            time.sleep(2)
            device.tap_and_type(0, 0, target_contact, editor_action="send") # 盲打搜索
            time.sleep(3)
            # 重新获取列表并点第一个
            elements = device.get_inventory()
            for e in elements:
                if target_contact in e['label']:
                    device.tap(*e['pos'])
                    time.sleep(2)
                    break
    
    # 3. 定位输入框并一键发送 (核心最优步骤)
    elements = device.get_inventory()
    input_box = next((e for e in elements if e['id'] == "compose_message_text"), None)
    
    if input_box:
        print(f"[*] 发现输入框，执行模型推荐的一键发送: '{msg_text}'")
        device.tap_and_type(input_box['pos'][0], input_box['pos'][1], msg_text, editor_action="send")
        print("[*] 动作已发出。")
        time.sleep(3)
        # 4. 校验
        elements = device.get_inventory()
        if any("SMS" in e['label'] or "message_status" in e['id'] for e in elements):
            print("\n✅ 最优路径 (补强版) 实测成功！")
        else:
            print("\n❌ 发送后未检测到状态变化。")
    else:
        print("[!] 还是没找到输入框。")

if __name__ == "__main__":
    test_optimal_path_v2()
