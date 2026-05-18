import subprocess
import time
import re

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

def check_content():
    # 尝试 3 次 Dump，防止系统还没刷出来
    for _ in range(3):
        run_adb(["shell", "uiautomator", "dump", "/sdcard/check.xml"])
        xml = run_adb(["shell", "cat", "/sdcard/check.xml"]).stdout
        # 匹配任何带 text 的 EditText
        match = re.search(r'text="([^"]*)"[^>]*class="android.widget.EditText"', xml)
        if match:
            return match.group(1)
        time.sleep(0.5)
    return "NOT_FOUND"

def test_combination(name, meta, keycode, second_key=None):
    print(f"\n[*] 尝试: {name} (meta={meta}, key={keycode})")
    
    # 1. 确保有内容
    current = check_content()
    if current == "" or current == "Text message" or current == "NOT_FOUND":
        run_adb(["shell", "input", "text", "REF_TEXT_123"])
        time.sleep(0.5)
        current = check_content()
    
    print(f"   起始内容: '{current}'")
    
    # 2. 执行组合键 (全选)
    run_adb(["shell", "input", "keyevent", "--metaState", str(meta), str(keycode)])
    time.sleep(0.2)
    
    # 3. 执行删除
    run_adb(["shell", "input", "keyevent", "67"])
    time.sleep(0.5)
    
    # 4. 检查
    res = check_content()
    if res == "" or res == "Text message":
        print(f"   [!!! SUCCESS !!!] {name} 彻底清空了内容！")
        return True
    else:
        print(f"   [FAILED] 残留: '{res}'")
        # 强制清空
        run_adb(["shell", "for i in $(seq 60); do input keyevent 67; done"])
        return False

def main():
    print("[*] 正在准备短信输入框...")
    run_adb(["shell", "input", "tap", "553", "2137"])
    time.sleep(1)

    # 更加全面的组合清单
    tests = [
        ("Ctrl+A (Standard)", 4096, 29),
        ("Ctrl+A (Left)", 8192, 29),
        ("Ctrl+A (Right)", 16384, 29),
        ("Ctrl+A (Combined)", 28672, 29),
        ("Shift+Home (Standard)", 1, 122),
        ("Shift+Home (Left)", 64, 122),
        ("Shift+Home (Combined)", 193, 122),
        ("Alt+A", 2, 29),
    ]

    for t in tests:
        test_combination(*t)

if __name__ == "__main__":
    main()
