import time
import subprocess

def adb_command(cmd):
    print(f"执行: adb {cmd}")
    result = subprocess.run(f"adb {cmd}", shell=True, capture_output=True, text=True)
    return result.stdout

def run_final_fix():
    print("\n--- 🍕 披萨店收割机：海底捞月版 ---")
    
    # 1. 回到详情页（假设我们已经通过刚才的运行停在了店面详情或照片页）
    # 为了稳妥，我们直接从详情页开始纠正
    print("Step 1: 确保回到详情页主页...")
    adb_command("shell input keyevent 4") # 如果在照片页，退回详情页
    time.sleep(2)
    
    # 2. 点击底部的悬浮 Call 按钮
    print("Step 2: 点击底部的‘悬浮固定’Call 按钮...")
    # 使用底部的坐标 [549, 2264]
    adb_command("shell input tap 549 2264")
    print("等待拨号盘弹出...")
    time.sleep(6) # 给模拟器多点反应时间
    
    # 3. 截图验证
    print("Step 3: 截取拨号盘画面...")
    adb_command("shell screencap -p /sdcard/real_dialer.png")
    adb_command("pull /sdcard/real_dialer.png profiling/")
    print("战果图已保存至 profiling/real_dialer.png")

if __name__ == "__main__":
    run_final_fix()
