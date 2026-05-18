import time
import os
import re
import json
from device_controller import ADBController

def force_pizza_search():
    device = ADBController()
    pkg = "com.google.android.apps.maps"
    query = "best pizza in San Francisco"
    
    print(f"[*] 🔨 开始强制攻坚 Pizza 任务...")
    device.open_app(pkg)
    time.sleep(6)
    
    # --- 阶段 1: 唤起搜索框 ---
    for attempt in range(3):
        print(f"[*] 尝试唤起搜索界面 (第 {attempt+1} 次)...")
        elements = device.get_inventory()
        # 找那个最像搜索入口的 (可能是 Layout 或 EditText)
        target = next((e for e in elements if "search_omnibox" in e['label'] or "Search here" in e['label']), None)
        
        if target:
            print(f"[*] 点击搜索入口: {target['label']} @ {target['pos']}")
            device.tap(*target['pos'])
            time.sleep(2)
            
            # 再次检查 UI，看是否进入了搜索模式
            new_elements = device.get_inventory()
            is_searching = any("back" in e['label'].lower() or "cancel" in e['label'].lower() for e in new_elements)
            
            if is_searching or len(new_elements) != len(elements):
                print("[*] ✅ 成功进入搜索界面！")
                # 在新界面里找那个 EditText
                edit_text = next((e for e in new_elements if "EditText" in e['label'] or "search" in e['label']), None)
                if edit_text:
                    device.tap(*edit_text['pos'])
                    time.sleep(1)
                    device.type(query, editor_action="search")
                    print(f"[*] 已注入搜索词: {query}")
                    break
        else:
            print("[!] 连入口都没找到，尝试盲点顶部...")
            device.tap(500, 200)
            time.sleep(2)

    time.sleep(8) # 等待搜索结果列表

    # --- 阶段 2: 逻辑过滤 ---
    print("[*] 正在扫描列表中的 Pizza 店...")
    elements = device.get_inventory()
    for e in elements:
        # 寻找评分 >= 4.6
        if re.search(r"4\.[6-9]|5\.0", e['label']):
            print(f"[*] 🎯 锁定高分店: {e['label']}")
            device.tap(*e['pos'])
            time.sleep(5)
            
            # 抓取电话
            inner_elements = device.get_inventory()
            for node in inner_elements:
                if "phone" in node['label'].lower() or re.search(r"\d{3}-\d{3}", node['label']):
                    print(f"[*] 🏆 最终战果 (电话): {node['label']}")
                    return
            print("[!] 进去了，但详情页没看到电话。")
            return
            
    print("[!] 任务失败：还是没搜出来或者没找到高分店。")

if __name__ == "__main__":
    force_pizza_search()
