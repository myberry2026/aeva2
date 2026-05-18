import time
import os
import re
from device_controller import ADBController

def test_pizza_v2_robust():
    device = ADBController()
    pkg = "com.google.android.apps.maps"
    query = "best pizza in San Francisco"
    
    print(f"[*] 🚀 启动 Pizza 补强版测试...")
    device.open_app(pkg)
    time.sleep(5)
    
    # 打印所有控件，看看搜索框到底是谁
    elements = device.get_inventory()
    print("[*] 当前 UI 扫描结果:")
    for e in elements:
        if "search" in e['label'].lower():
            print(f"    >>> 疑似搜索框: {e['label']} (ID: {e['id']}) @ {e['pos']}")

    # 尝试点那个看起来最像搜索框的
    search_box = next((e for e in elements if "search" in e['label'].lower()), None)
    if not search_box:
        # 兜底：直接点顶部中央
        print("[*] 没找到明确的搜索框，尝试盲点顶部 [500, 100]")
        device.tap(500, 100)
    else:
        print(f"[*] 点击搜索框: {search_box['label']}")
        device.tap(*search_box['pos'])
    
    time.sleep(2)
    device.type(query, editor_action="search")
    print(f"[*] 已输入: {query}")
    time.sleep(8) # 地图加载慢，多等会儿

    # 检查结果列表
    elements = device.get_inventory()
    print(f"[*] 搜索后发现 {len(elements)} 个控件")
    
    target_shop = None
    for e in elements:
        # 寻找评分。注意：Maps 的评分通常在 label 里写着 "4.7 stars"
        if re.search(r"4\.[6-9]|5\.0", e['label']):
            print(f"[*] 找到符合条件的餐厅: {e['label']}")
            target_shop = e
            break
    
    if target_shop:
        device.tap(*target_shop['pos'])
        time.sleep(5)
        # 找电话
        elements = device.get_inventory()
        phone = next((e for e in elements if "phone" in e['label'].lower() or re.search(r"\d{3}", e['label'])), None)
        if phone:
            print(f"[*] ✅ 最终战果: {phone['label']}")
        else:
            print("[!] 详情页里没翻到电话。")
    else:
        print("[!] 还是没搜出来或者评分太低。")

if __name__ == "__main__":
    test_pizza_v2_robust()
