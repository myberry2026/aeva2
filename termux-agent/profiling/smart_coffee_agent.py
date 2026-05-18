
import os
import subprocess
import time
import xml.etree.ElementTree as ET
import re

class SmartAgent:
    def __init__(self, target_phone="1234567890"): # 默认发给谁
        self.target_phone = target_phone

    def run_adb(self, cmd):
        return subprocess.check_output(cmd, shell=True).decode('utf-8')

    def get_bounds(self, xml_path, pattern):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for node in root.iter():
                text = node.attrib.get('text', '')
                desc = node.attrib.get('content-desc', '')
                if re.search(pattern, text, re.I) or re.search(pattern, desc, re.I):
                    m = re.findall(r'\d+', node.attrib.get('bounds', ''))
                    if len(m) == 4:
                        return (int(m[0])+int(m[2]))//2, (int(m[1])+int(m[3]))//2
        except: return None
        return None

    def execute_mission(self, coffee_query, report_to):
        print(f"🚀 任务开始：寻找 {coffee_query} 并通知 {report_to}")

        # 1. Intent 瞬移：搜索
        print("➡️ 步骤 1: Intent 搜索空降...")
        self.run_adb(f"adb shell am start -a android.intent.action.VIEW -d 'geo:0,0?q={coffee_query.replace(' ', '+')}'")
        time.sleep(4)

        # 2. 语义拾取：点击第一个高分项 (假设咱们已经划好了，直接点列表第一项)
        # 这里简化一下，直接点搜索结果区域
        print("➡️ 步骤 2: 语义拾取目标...")
        self.run_adb("adb shell input tap 540 1800") 
        time.sleep(3)

        # 3. 提取号码：通过拨号盘 Intent
        print("➡️ 步骤 3: 触发拨号 Intent 提取号码...")
        self.run_adb("adb shell uiautomator dump /sdcard/detail.xml")
        self.run_adb("adb pull /sdcard/detail.xml profiling/detail.xml")
        
        # 寻找“Call”按钮并点击
        call_pos = self.get_bounds("profiling/detail.xml", "Call")
        if call_pos:
            self.run_adb(f"adb shell input tap {call_pos[0]} {call_pos[1]}")
            time.sleep(3)
            
            # 在拨号盘抓取号码
            self.run_adb("adb shell uiautomator dump /sdcard/dialer.xml")
            self.run_adb("adb pull /sdcard/dialer.xml profiling/dialer.xml")
            
            # 正则匹配拨号盘上的数字
            with open("profiling/dialer.xml", "r") as f:
                xml_content = f.read()
            phone_match = re.search(r'([0-9]{3})[-. ]?([0-9]{3})[-. ]?([0-9]{4})', xml_content)
            
            if phone_match:
                found_phone = "".join(phone_match.groups())
                print(f"✅ 抓到号码: {found_phone}")
                
                # 4. Intent 闭环：发送短信
                print(f"➡️ 步骤 4: Intent 瞬移至短信发送给 {report_to}...")
                # 重点：改用英文 Body 避免编码问题，并使用单引号包裹整个 adb 指令
                body = f"Found coffee shop number: {found_phone}"
                self.run_adb(f"adb shell 'am start -a android.intent.action.SENDTO -d sms:{report_to} --es sms_body \"{body}\"'")
                time.sleep(2)
                
                # 5. 语义拾取：寻找发送按钮并点击
                print("➡️ 步骤 5: 语义定位发送按钮...")
                self.run_adb("adb shell uiautomator dump /sdcard/sms_ui.xml")
                self.run_adb("adb pull /sdcard/sms_ui.xml profiling/sms_ui.xml")
                send_pos = self.get_bounds("profiling/sms_ui.xml", "Send SMS")
                if send_pos:
                    print(f"➡️ 步骤 5: 临门一脚，点击发送坐标 {send_pos}！")
                    self.run_adb(f"adb shell input tap {send_pos[0]} {send_pos[1]}")
                    print("🎉 任务圆满完成！")
                else:
                    # 如果找不到 content-desc，尝试点击咱们刚才确定的保底坐标
                    print("⚠️ 未找到语义发送按钮，尝试保底坐标...")
                    self.run_adb("adb shell input tap 994 2251")
                    print("🎉 任务圆满完成（保底路径）！")
            else:
                print("❌ 拨号盘没抓到号码。")
        else:
            print("❌ 没找到拨号按钮。")

if __name__ == "__main__":
    agent = SmartAgent()
    # 模拟任务：搜 Moksha Coffee，发给 10086 (演示用)
    agent.execute_mission("Moksha Coffee", "10086")
