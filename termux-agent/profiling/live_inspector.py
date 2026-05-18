
import os
import time
import json
from device_controller import ADBController, BridgeController
from screen_converter import screen_to_inventory
from adb_utils import _adb_ensure_keyboard

def start_live_inspector(mode="adb", interval=2):
    """
    实时监控程序：广播截屏和优化的 XML 清单。
    """
    # 1. 初始化控制器
    if mode == "bridge":
        controller = BridgeController(bridge_url="http://localhost:8765")
    else:
        controller = ADBController()

    print(f"📡 实时监控已启动 (模式: {mode})")
    
    # 核心增强：确保驱动就绪
    print("⌨️  正在同步输入驱动 (ADBKeyboard)...")
    if _adb_ensure_keyboard():
        print("✅ 驱动就绪：支持中文输入与 IME Action")
    else:
        print("⚠️ 驱动告警：未检测到 ADBKeyboard，高级功能可能受限")

    print(f"每 {interval} 秒刷新一次...")
    print("监控数据将保存在 profiling/live_status.json 和 profiling/live_screen.png")

    try:
        while True:
            # A. 抓取 Inventory (优化的 XML Tree)
            inventory = controller.get_inventory()
            
            # B. 抓取 截屏
            screenshot_path = "profiling/live_screen.png"
            controller.take_screenshot(screenshot_path)
            
            # C. 汇总状态
            status = {
                "timestamp": time.strftime("%H:%M:%S"),
                "inventory_count": len(inventory),
                "interactive_elements": [
                    {"id": item["id"], "label": item["label"], "pos": item["pos"]} 
                    for item in inventory if "Widget" not in item["label"]
                ]
            }
            
            # D. “广播” (保存到文件供外部读取)
            with open("profiling/live_status.json", "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)

            # E. 实时回显到终端
            os.system("clear")
            print(f"🕒 [{status['timestamp']}] 屏幕更新完毕！")
            print(f"📊 发现 {len(inventory)} 个可操作控件")
            print("-" * 50)
            for item in status["interactive_elements"][:15]: # 只显示前15个重要的
                print(f"[{item['id']}] {item['label']} @ {item['pos']}")
            if len(status["interactive_elements"]) > 15:
                print(f"... 还有 {len(status['interactive_elements']) - 15} 个控件未列出")
            print("-" * 50)
            print("Ctrl+C 可停止监控")
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 监控已停止。")

if __name__ == "__main__":
    # 默认使用 ADB 模式，如果 Bridge 可用也可以切换
    start_live_inspector(mode="adb")
