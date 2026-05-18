import time
import os
from device_controller import BridgeController, ADBController

# 100% 还原模型建议的逻辑
def test_exact_model_path():
    device = ADBController()
    pkg = "com.google.android.apps.messaging"
    
    print("[*] 🧪 开始 100% 还原模型最优路径...")
    
    # 模型步 1: Launch
    print(f"[*] Action: Launch {pkg}")
    device.open_app(pkg)
    
    # 模型步 2: Wait for Anchor (id:conversation_title == '10086')
    print("[*] Action: Waiting for id:conversation_title with value '10086'...")
    found_anchor = False
    for _ in range(10): # 最多等 10 秒
        elements = device.get_inventory()
        # 模型说的 Anchor
        anchor = next((e for e in elements if "conversation_title" in e['label'] and "10086" in e['label']), None)
        if anchor:
            print(f"[*] Found Anchor: {anchor['label']}")
            found_anchor = True
            break
        time.sleep(1)
    
    if not found_anchor:
        print("[!] 失败：模型说的 Anchor (10086 标题) 没出现！")
        return

    # 模型步 3: Type in Target (id:compose_message_text)
    print("[*] Action: Typing in id:compose_message_text with action='send'...")
    elements = device.get_inventory()
    target = next((e for e in elements if "compose_message_text" in e['label']), None)
    
    if target:
        device.tap_and_type(target['pos'][0], target['pos'][1], "Hello from Model Logic", editor_action="send")
        print("[*] ✅ 动作已发出。")
    else:
        print("[!] 失败：模型说的 Target (输入框) 没找到！")

if __name__ == "__main__":
    test_exact_model_path()
