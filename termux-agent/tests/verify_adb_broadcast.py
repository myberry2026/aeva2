import subprocess
import time
import re

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

def check_content():
    run_adb(["shell", "uiautomator", "dump", "/sdcard/check.xml"])
    xml = run_adb(["shell", "cat", "/sdcard/check.xml"]).stdout
    match = re.search(r'text="([^"]*)"[^>]*class="android.widget.EditText"', xml)
    return match.group(1) if match else "NOT_FOUND"

def main():
    print("[*] 正在准备短信输入框 [553, 2137]...")
    run_adb(["shell", "input", "tap", "553", "2137"])
    time.sleep(1)
    
    # 1. 填入长文本作为测试
    print("[*] 正在填入干扰文本...")
    run_adb(["shell", "input", "text", "ThisIsLongTextThatNeedsToBeCleared1234567890"])
    time.sleep(1)
    print(f"    目前内容: '{check_content()}'")

    # 2. 尝试使用 ADBKeyBoard 的广播指令进行“一键覆盖”
    print("\n[*] 正在尝试 ADBKeyBoard 广播覆盖方案...")
    # 发送空字符串广播，理论上应该瞬间清空
    run_adb(["shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT", "--es", "msg", "CLEAN_SUCCESS"])
    time.sleep(1)
    
    # 3. 检查
    res = check_content()
    if "CLEAN_SUCCESS" in res:
        print(f"    [!!! BINGO !!!] 广播覆盖成功！最终内容: '{res}'")
        print("    结论：这是最稳的方案，直接覆盖，不需要全选。")
    else:
        print(f"    [FAILED] 广播覆盖无效，残留或未变化: '{res}'")

if __name__ == "__main__":
    main()
