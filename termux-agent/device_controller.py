import os
import time
import subprocess
import re
from screen_converter import xml_to_inventory, json_to_inventory
from adb_utils import _run_adb, _adb_get_screen_size, _adb_get_installed_apps, _adb_type, log
from intent_library import get_intent


class DeviceController:
    """抽象基类，定义所有设备操作的标准接口。"""
    def tap(self, x, y): raise NotImplementedError()
    def long_press(self, x, y, duration=1000): raise NotImplementedError()
    def swipe(self, x1, y1, x2, y2, duration=500): raise NotImplementedError()
    def type(self, text, clear_first=True, editor_action=None): raise NotImplementedError()
    def tap_and_type(self, x, y, text, clear_first=True, editor_action=None): raise NotImplementedError()
    def back(self): raise NotImplementedError()
    def home(self): raise NotImplementedError()
    def open_app(self, pkg): raise NotImplementedError()
    def open_url(self, uri, action="android.intent.action.VIEW"): raise NotImplementedError()
    def smart_teleport(self, task, query=None): raise NotImplementedError()
    
    # Aliases
    teleport = open_url
    go_to = smart_teleport
    def get_screen_size(self): raise NotImplementedError()
    def get_inventory(self): raise NotImplementedError()
    def get_installed_apps(self): raise NotImplementedError()
    def scroll_down(self):
        """通用的滚屏逻辑：从屏幕 80% 处滑动到 20% 处。"""
        w, h = self.get_screen_size()
        x = w // 2
        self.swipe(x, int(h * 0.8), x, int(h * 0.2), duration=500)

    def scroll_up(self):
        """通用的滚屏逻辑：从屏幕 20% 处滑动到 80% 处。"""
        w, h = self.get_screen_size()
        x = w // 2
        self.swipe(x, int(h * 0.2), x, int(h * 0.8), duration=500)

    def take_screenshot(self, path): raise NotImplementedError()
    def overlay(self, text): raise NotImplementedError()


class ADBController(DeviceController):
    """原生 ADB 适配器。"""
    def tap(self, x, y):
        _run_adb(["shell", "input", "tap", str(x), str(y)])

    def long_press(self, x, y, duration=1000):
        _run_adb(["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration)])

    def swipe(self, x1, y1, x2, y2, duration=500):
        _run_adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])

    def type(self, text, clear_first=True, editor_action=None):
        _adb_type(text, clear_first=clear_first, editor_action=editor_action)
    
    def tap_and_type(self, x, y, text, clear_first=True, editor_action=None):
        self.tap(x, y)
        time.sleep(1.0)
        self.type(text, clear_first=clear_first, editor_action=editor_action)

    def back(self):
        _run_adb(["shell", "input", "keyevent", "4"])

    def home(self):
        _run_adb(["shell", "input", "keyevent", "3"])

    def open_url(self, uri, action="android.intent.action.VIEW"):
        """通过 Intent URI 直接跳转到 App 特定页面。"""
        # 使用引号包裹 URI 避免 shell 解析特殊字符如 & 和 ?
        _run_adb(["shell", "am", "start", "-a", action, "-d", f'"{uri}"'])
    
    def smart_teleport(self, task, query=None):
        """
        超级语义传送门 (Smart Portal) v2.0
        
        支持任务: map, route, sms, call, email, alarm, calendar, youtube, twitter, reddit, settings, wifi, etc.
        详情请参考 intent_library.py
        """
        # 1. 优先检查硬件级系统命令 (如 wifi_on)
        hw_commands = {
            "wifi_on":  "svc wifi enable",
            "wifi_off": "svc wifi disable"
        }
        if task in hw_commands:
            log(f"💻 执行底层指令: {hw_commands[task]}")
            _run_adb(["shell"] + hw_commands[task].split())
            return

        # 2. 从意图仓库获取 Intent (Action, URI, Extras)
        action, uri, extras = get_intent(task, query)
        
        if action:
            log(f"🌌 语义传送: {task}({query or ''}) -> {action}")
            cmd = ["shell", "am", "start", "-a", action]
            if uri:
                cmd.extend(["-d", f'"{uri}"'])
            if extras:
                cmd.extend(extras)
            
            _run_adb(cmd)
        else:
            # 3. 兜底逻辑：作为原始 URI 处理
            log(f"⚠️ 仓库中未找到任务 '{task}'，尝试直接打开...")
            self.open_url(task)

    # 别名定义 (Alias)
    teleport = open_url
    go_to = smart_teleport

    def open_app(self, pkg):
        _run_adb(["shell", "am", "force-stop", pkg])
        time.sleep(0.5)
        _run_adb(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])

    def get_screen_size(self):
        return _adb_get_screen_size()

    def get_inventory(self):
        _run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
        xml_data = _run_adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
        if not xml_data: return []
        w, _ = self.get_screen_size()
        return xml_to_inventory(xml_data, w)

    def get_installed_apps(self):
        return _adb_get_installed_apps()

    def take_screenshot(self, path):
        _run_adb(["shell", "screencap", "-p", "/sdcard/screen.png"])
        _run_adb(["pull", "/sdcard/screen.png", path])
        try:
            from PIL import Image
            with Image.open(path) as img:
                img.convert("RGB").save(path.replace(".png", ".jpg"), "JPEG", quality=40)
                os.replace(path.replace(".png", ".jpg"), path)
        except Exception:
            pass

    def overlay(self, text):
        pass


class BridgeController(DeviceController):
    """Bridge Android 适配器（通过 HTTP API 控制手机）。"""
    def __init__(self, bridge_url="http://localhost:8765", token=""):
        from bridge_client import BridgeClient
        self.client = BridgeClient(bridge_url, token=token)

    def tap(self, x, y):
        return self.client.tap(x, y)

    def long_press(self, x, y, duration=1000):
        return self.client.long_press(x, y, duration)

    def swipe(self, x1, y1, x2, y2, duration=500):
        dy = y2 - y1
        dx = x2 - x1
        if abs(dy) >= abs(dx):
            direction = "up" if dy > 0 else "down"
        else:
            direction = "right" if dx > 0 else "left"
        dist = max(abs(dx), abs(dy))
        if dist > 800:
            distance = "long"
        elif dist > 400:
            distance = "medium"
        else:
            distance = "short"
        return self.client.swipe(direction, distance)

    def type(self, text, clear_first=False, editor_action=None):
        return self.client.type_text(text, clear_first=clear_first, editor_action=editor_action)

    def tap_and_type(self, x, y, text, clear_first=False, editor_action=None):
        return self.client.tap_and_type(x, y, text, clear_first=clear_first, editor_action=editor_action)

    def back(self):
        return self.client.back()

    def home(self):
        return self.client.home()

    def open_app(self, pkg):
        return self.client.open_app(pkg)

    def open_url(self, uri, action="android.intent.action.VIEW"):
        return self.client.send_intent(action, data_uri=uri)

    def smart_teleport(self, task, query=None):
        action, uri, extras = get_intent(task, query)

        if action:
            log(f"🌌 语义传送: {task}({query or ''}) -> {action}")
            extras_dict = {}
            if extras:
                i = 0
                while i < len(extras) - 2:
                    extras_dict[extras[i + 1]] = extras[i + 2]
                    i += 3
            return self.client.send_intent(action, data_uri=uri, extras=extras_dict or None)
        else:
            log(f"⚠️ 仓库中未找到任务 '{task}'，尝试直接打开...")
            return self.open_url(task)

    # 别名
    teleport = open_url
    go_to = smart_teleport

    def get_screen_size(self):
        size = self.client.get_screen_size()
        return (size[0], size[1])

    def get_inventory(self):
        data = self.client.read_screen(bounds=True)
        w, _ = self.get_screen_size()
        return json_to_inventory(data, w)

    def get_installed_apps(self):
        return self.client.get_installed_apps()

    def take_screenshot(self, path):
        res = self.client.screenshot(path)
        try:
            from PIL import Image
            with Image.open(path) as img:
                img.convert("RGB").save(path.replace(".png", ".jpg"), "JPEG", quality=40)
                os.replace(path.replace(".png", ".jpg"), path)
        except Exception:
            pass
        return res

    def overlay(self, text):
        return self.client.overlay(text)
