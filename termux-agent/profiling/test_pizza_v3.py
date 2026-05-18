import time
import os
import re
from device_controller import ADBController

def test_pizza_v3_sniper():
    device = ADBController()
    pkg = "com.google.android.apps.maps"
    query = "best pizza in San Francisco"
    
    print(f"[*] 🚀 启动 Pizza 狙击版测试 (V3)...")
    device.open_app(pkg)
    time.sleep(6)
    
    elements = device.get_inventory()
    # 精准寻找那个 EditText
    edit_box = next((e for e in elements if "search_omnibox_text_box" in e['label'] or "EditText" in e['label']), None)
    
    if edit_box:
        print(f"[*] 锁定目标 EditText: {edit_box['label']} @ {edit_box['pos']}")
        device.tap(*edit_box['pos'])
        time.sleep(2) # 给足唤醒时间
        device.type(query, editor_action="search")
        print(f"[*] 注入指令: {query}")
    else:
        print("[!] 没找到 EditText，尝试盲点 [400, 212]")
        device.tap(400, 212)
        time.sleep(2)
        device.type(query, editor_action="search")

    time.sleep(10) # 地图加载真的很慢

    # 结果分析
    elements = device.get_inventory()
    print(f"[*] 搜索后探测到 {len(elements)} 个元素")
    
    # 找评分 >= 4.6
    for e in elements:
        # Maps 的评分有时是 "4.7 (2.3k)" 这种格式
        match = re.search(r"(4\.[6-9]|5\.0)", e['label'])
        if match:
            print(f"[*] 🎯 命中目标! 餐厅: {e['label']}")
            device.tap(*e['pos'])
            time.sleep(5)
            # 抓电话
            elements = device.get_inventory()
            for inner in elements:
                if "phone" in inner['label'].lower() or re.search(r"\d{3}-\d{3}", inner['label']):
                    print(f"[*] ✅ 任务达成! 电话: {inner['label']}")
                    return
            print("[!] 进去了，但没看到电话。")
            return
    
    print("[!] 列表里还是没看到高分店。")

if __name__ == "__main__":
    test_pizza_v3_sniper()
