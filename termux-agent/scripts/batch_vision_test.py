import subprocess
import time
import base64
import requests
import os

def log(msg):
    print(f"[*] {msg}")

def run_adb(args):
    return subprocess.run(["adb"] + args, capture_output=True, text=True)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def query_ollama(model, prompt, image_base64):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_base64],
        "stream": False
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        return response.json().get("response", "无返回内容")
    except Exception as e:
        return f"请求出错: {e}"

# 定义 10 个测试场景的操作
scenarios = [
    {
        "name": "主屏幕",
        "action": lambda: run_adb(["shell", "input", "keyevent", "3"]), # Home 键
        "prompt": "这张截图中显示的是手机主屏幕吗？你看到了哪些图标？"
    },
    {
        "name": "计算器",
        "action": lambda: run_adb(["shell", "monkey", "-p", "com.android.calculator2", "1"]),
        "prompt": "请识别这个应用。屏幕上的数字键和操作符清晰吗？"
    },
    {
        "name": "设置-电池",
        "action": lambda: run_adb(["shell", "am", "start", "-a", "android.intent.action.POWER_USAGE_SUMMARY"]),
        "prompt": "这是电池设置界面吗？能否看到当前电量百分比或使用情况？"
    },
    {
        "name": "时钟-闹钟",
        "action": lambda: run_adb(["shell", "am", "start", "-n", "com.android.deskclock/com.android.deskclock.DeskClock"]),
        "prompt": "这张截图里的时间是多少？有闹钟开启吗？"
    },
    {
        "name": "下拉通知栏",
        "action": lambda: (run_adb(["shell", "input", "keyevent", "3"]), time.sleep(1), run_adb(["shell", "cmd", "statusbar", "expand-notifications"])),
        "prompt": "屏幕上方是否拉出了通知栏？你看到了哪些快捷开关（如Wi-Fi、蓝牙）？"
    },
    {
        "name": "设置-关于手机",
        "action": lambda: run_adb(["shell", "am", "start", "-a", "android.settings.DEVICE_INFO_SETTINGS"]),
        "prompt": "这张图显示的是设备信息吗？你能读出 Android 版本或者设备名称吗？"
    },
    {
        "name": "文件管理器",
        "action": lambda: run_adb(["shell", "monkey", "-p", "com.android.documentsui", "1"]),
        "prompt": "这是文件管理器吗？屏幕上有哪些文件夹或文件分类？"
    },
    {
        "name": "联系人列表",
        "action": lambda: run_adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "content://contacts/people"]),
        "prompt": "这是联系人界面吗？是否显示了姓名列表？"
    },
    {
        "name": "日历",
        "action": lambda: run_adb(["shell", "am", "start", "-n", "com.android.calendar/com.android.calendar.AllInOneActivity"]),
        "prompt": "这是日历应用吗？显示的是哪个月份或日期？"
    },
    {
        "name": "多任务切换",
        "action": lambda: run_adb(["shell", "input", "keyevent", "187"]), # App Switcher
        "prompt": "这是多任务切换界面吗？你能看到几个后台应用的预览图？"
    }
]

def main():
    model_name = "gemma4:latest"
    results = []

    for i, sc in enumerate(scenarios):
        log(f"--- 测试项目 {i+1}: {sc['name']} ---")
        
        # 执行动作
        sc['action']()
        time.sleep(3) # 等待加载
        
        # 截图
        img_path = f"test_scene_{i+1}.png"
        with open(img_path, "wb") as f:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f)
        
        # 识别
        img_b64 = encode_image(img_path)
        response = query_ollama(model_name, sc['prompt'], img_b64)
        
        log(f"AI 结果预览: {response[:100]}...")
        results.append({
            "scene": sc['name'],
            "response": response
        })

    # 输出总结
    print("\n" + "="*80)
    print("BATCH TEST REPORT - GEMMA4 VISION")
    print("="*80)
    for r in results:
        print(f"\n[场景: {r['scene']}]")
        print(f"AI 回复: {r['response']}")
        print("-" * 40)

if __name__ == "__main__":
    main()
