import time
import os
import re
from device_controller import ADBController

def test_pizza_exact_path():
    device = ADBController()
    pkg = "com.google.android.apps.maps"
    query = "best pizza in San Francisco"
    
    print(f"[*] 🧪 启动 Pizza 任务模型路径验证...")
    
    # 1. 启动
    device.open_app(pkg)
    time.sleep(5)
    
    # 2. 搜索 (模型说 ID 2 是搜索框，我们动态找一下更稳，但优先看 ID 2)
    elements = device.get_inventory()
    search_box = next((e for e in elements if "search" in e['label'].lower() or e['id'] == 2), None)
    
    if search_box:
        print(f"[*] 发现搜索框: {search_box['label']}，输入 '{query}'")
        device.tap_and_type(search_box['pos'][0], search_box['pos'][1], query, editor_action="search")
        time.sleep(5)
    else:
        print("[!] 没找到搜索框。")
        return

    # 3. 筛选 4.6 分以上的店
    print("[*] 正在筛选 4.6 分以上的餐厅...")
    elements = device.get_inventory()
    target_shop = None
    for e in elements:
        # 寻找包含 4.[6-9] 或 5.0 的文本
        m = re.search(r"4\.[6-9]|5\.0", e['label'])
        if m and ("star" in e['label'].lower() or "rating" in e['label'].lower() or "4." in e['label']):
            print(f"[*] 发现高分餐厅: {e['label']}")
            target_shop = e
            break
    
    if target_shop:
        device.tap(*target_shop['pos'])
        time.sleep(4)
    else:
        print("[!] 列表中没看到 4.6 分以上的店。")
        return

    # 4. 抓取电话
    print("[*] 正在详情页寻找电话号码...")
    elements = device.get_inventory()
    phone_node = next((e for e in elements if "phone" in e['label'].lower() or re.search(r"\d{3}-\d{3}-\d{4}", e['label'])), None)
    
    if phone_node:
        print(f"[*] ✅ 成功抓取电话: {phone_node['label']}")
    else:
        print("[!] 详情页没找到电话。")

    # 5. 返回
    print("[*] 正在返回主界面...")
    device.back()
    time.sleep(1)
    device.back()
    print("[*] 任务结束。")

if __name__ == "__main__":
    test_pizza_exact_path()
