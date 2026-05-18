import time
import os
from device_controller import BridgeController, ADBController

# 配置环境
BRIDGE_URL = os.getenv("BRIDGE_URL", "http://127.0.0.1:8765")
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "")
BACKEND = os.getenv("CONTROL_BACKEND", "bridge").lower()

def get_device():
    if BACKEND == "bridge":
        return BridgeController(BRIDGE_URL, BRIDGE_TOKEN)
    return ADBController()

def test_optimal_path():
    device = get_device()
    pkg = "com.google.android.apps.messaging"
    target_contact = "10086"
    msg_text = "Hello"

    print(f"[*] 🚀 启动最优路径测试 (后端: {BACKEND})")

    # 1. 启动并进入短信
    print(f"[*] Step 1: 启动 {pkg}")
    device.open_app(pkg)
    time.sleep(3)

    # 2. 查找目标会话并进入 (假设已经在这个会话里，或者点击它)
    # 我们先 dump 一下 UI 看看在哪
    elements = device.get_inventory()
    target_node = None
    for e in elements:
        if target_contact in e['label'] or e['id'] == "conversation_title":
            target_node = e
            break
    
    if not target_node:
        print(f"[!] 找不到联系人 {target_contact}，尝试直接寻找输入框...")
    else:
        print(f"[*] 确认当前在 {target_node['label']} 的会话中")

    # 3. 定位输入框并一键发送
    print(f"[*] Step 2: 定位输入框并发送 '{msg_text}' (带 editor_action='send')")
    input_box = None
    for e in elements:
        if e['id'] == "compose_message_text" or "Text message" in e['label']:
            input_box = e
            break
    
    if input_box:
        pos = input_box['pos']
        # 执行一键发送
        device.tap_and_type(pos[0], pos[1], msg_text, editor_action="send")
        print(f"[*] 动作已发出: 在 {pos} 输入并触发发送")
    else:
        print("[!] 没找到输入框！路径失败。")
        return

    # 4. 校验结果
    print("[*] Step 3: 等待 3 秒进行结果校验...")
    time.sleep(3)
    new_elements = device.get_inventory()
    success = False
    for e in new_elements:
        if "SMS" in e['label'] or "message_status" in e['id']:
            print(f"[*] 发现发送状态: {e['label']}")
            success = True
            break
    
    if success:
        print("\n" + "✅"*20)
        print("✅ 最优路径实测成功！3 步搞定！")
        print("✅"*20 + "\n")
    else:
        print("\n" + "❌"*20)
        print("❌ 校验失败：未发现发送成功的状态位。")
        print("❌"*20 + "\n")

if __name__ == "__main__":
    test_optimal_path()
