import time
import subprocess

def adb_command(cmd):
    print(f"执行: adb {cmd}")
    result = subprocess.run(f"adb {cmd}", shell=True, capture_output=True, text=True)
    return result.stdout

def run_final_demo():
    print("\n--- 🍕 披萨店收割机：终极实战演示 ---")
    
    # 1. 回到地图首页并重置
    print("Step 1: 启动地图并重置状态...")
    adb_command("shell am start -n com.google.android.apps.maps/com.google.android.maps.MapsActivity")
    time.sleep(3)
    
    # 2. 点击搜索框，清空并输入
    print("Step 2: 输入搜索词并回车...")
    adb_command("shell input tap 500 150") # 点击搜索框
    time.sleep(1)
    # 暴力清空（模拟按下全选+删除）
    adb_command("shell input keyevent 123") # MOVE_END
    for _ in range(20): adb_command("shell input keyevent 67") # BACKSPACE
    adb_command("shell input text 'best%spizza%sin%sSan%sFrancisco'") # 空格用%s代替
    time.sleep(1)
    adb_command("shell input keyevent 66") # 核心：回车触发
    print("等待结果加载...")
    time.sleep(6)
    adb_command("shell screencap -p /sdcard/step2_search.png")

    # 3. 强制开启列表模式
    print("Step 3: 强制切换至列表模式...")
    # 使用刚才 XML 里的坐标 [866, 2211]
    adb_command("shell input tap 866 2211")
    time.sleep(3)
    adb_command("shell screencap -p /sdcard/step3_list.png")

    # 4. 点击 Sforno 店名进入详情
    print("Step 4: 点击 Sforno 进入详情页...")
    # 使用刚才 XML 里的店名坐标 [500, 860]
    adb_command("shell input tap 500 860")
    time.sleep(5)
    adb_command("shell screencap -p /sdcard/step4_detail.png")

    # 5. 点击详情页的 Call 按钮
    print("Step 5: 最终拨号攻击！...")
    # 使用详情页 XML 里的 Call 坐标 [755, 514]
    adb_command("shell input tap 755 514")
    time.sleep(3)
    adb_command("shell screencap -p /sdcard/step5_dialer.png")

    # 6. 把过程图都拉回来
    print("\n--- 演示结束，拉取战果图 ---")
    adb_command("pull /sdcard/step2_search.png profiling/")
    adb_command("pull /sdcard/step3_list.png profiling/")
    adb_command("pull /sdcard/step4_detail.png profiling/")
    adb_command("pull /sdcard/step5_dialer.png profiling/")
    print("所有截图已保存至 profiling/ 目录。")

if __name__ == "__main__":
    run_final_demo()
