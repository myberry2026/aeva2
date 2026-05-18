"""
bridge_client.py — bridge-android HTTP 适配器

将 bridge-android bridge 的 HTTP API 封装为与当前 adb_* 函数相同签名的调用，
用于替换 humanoid_agent.py 中的 ADB 控制层。

用法:
    from bridge_client import BridgeClient
    hc = BridgeClient("http://localhost:8765", token="abc123")
    hc.tap(540, 1200)
    hc.type_text("hello", clear_first=True)
    img_path = hc.screenshot("/tmp/screen.jpg")
"""

import base64
import json
import os
import time
import requests
from typing import Optional


class BridgeClient:
    def __init__(self, base_url: str = "http://localhost:8765", token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._screen_w = 1080
        self._screen_h = 2400

    def _headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _get(self, path: str, timeout: float = 30) -> dict:
        r = requests.get(f"{self.base_url}{path}", headers=self._headers(), timeout=timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, payload: dict, timeout: float = 30) -> dict:
        r = requests.post(f"{self.base_url}{path}", json=payload, headers=self._headers(), timeout=timeout)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str, timeout: float = 30) -> dict:
        r = requests.delete(f"{self.base_url}{path}", headers=self._headers(), timeout=timeout)
        r.raise_for_status()
        return r.json()

    # ── 健康检查 ──────────────────────────────────────────────────────────────

    def ping(self) -> dict:
        """检查 bridge 和 AX service 状态"""
        return self._get("/ping", timeout=5)

    def is_ready(self) -> bool:
        """bridge 可用且 AX service 正在运行"""
        try:
            data = self.ping()
            return data.get("accessibilityService", False)
        except Exception:
            return False

    # ── 屏幕信息 ──────────────────────────────────────────────────────────────

    def get_screen_size(self) -> tuple:
        """从 screenshot 响应获取屏幕尺寸"""
        try:
            data = self._get("/screenshot", timeout=10)
            result = data.get("data", data)
            w = result.get("width", 1080)
            h = result.get("height", 2400)
            self._screen_w, self._screen_h = int(w), int(h)
        except Exception:
            pass
        return (self._screen_w, self._screen_h)

    def read_screen(self, bounds: bool = True) -> dict:
        """读取当前屏幕的 accessibility 树 (ScreenNode JSON)"""
        return self._get(f"/screen?bounds={str(bounds).lower()}")

    def screenshot(self, path: str) -> str:
        """截图并保存到 path，返回 path"""
        data = self._get("/screenshot", timeout=15)
        if not data:
            raise RuntimeError("screenshot 接口返回空数据")
        result = data.get("data", data)
        if not result:
            raise RuntimeError("screenshot 响应中没有 data 字段")
        img_b64 = result.get("image", "")
        if not img_b64:
            raise RuntimeError("screenshot 返回空图片数据")
        img_bytes = base64.b64decode(img_b64)
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(img_bytes)
        # 更新屏幕尺寸
        w = result.get("width")
        h = result.get("height")
        if w and h:
            self._screen_w, self._screen_h = int(w), int(h)
        return path

    # ── 应用列表 ──────────────────────────────────────────────────────────────

    def get_installed_apps(self) -> list:
        """返回 launcher app 包名列表"""
        try:
            data = self._get("/apps")
            # Bridge 返回 {"apps": [{"packageName": "...", "label": "..."}], "count": ...}
            if isinstance(data, dict):
                apps = data.get("apps", [])
                if isinstance(apps, list):
                    return [app.get("packageName", "") for app in apps if app.get("packageName")]
            # 兼容旧版或直接返回列表的情况
            if isinstance(data, list):
                return [app.get("packageName", "") for app in data if app.get("packageName")]
            return []
        except Exception:
            return []

    # ── 输入操作 ──────────────────────────────────────────────────────────────

    def tap(self, x: int, y: int):
        """点击坐标 (x, y)"""
        return self._post("/tap", {"x": x, "y": y})

    def long_press(self, x: int, y: int, duration: int = 1000):
        """长按坐标 (x, y)，duration 毫秒"""
        return self._post("/long_press", {"x": x, "y": y, "duration": duration})

    def drag(self, x1, y1, x2, y2, duration=500):
        """拖拽动作。"""
        return self._post("/drag", {
            "startX": x1, "startY": y1, 
            "endX": x2, "endY": y2, 
            "duration": duration
        })

    # editor_action → press_key 映射（bridge 的 /press_key 支持这些 key name）
    _EDITOR_ACTION_KEYS = {
        "search": "search",
        "go": "enter",
        "send": "enter",
        "done": "enter",
        "next": "enter",
        "previous": "enter",
    }

    def type_text(self, text: str, clear_first: bool = False, editor_action: Optional[str] = None):
        """输入文字，可选附带 editor action（search/send/done/go/next）。"""
        result = self._post("/type", {"text": text, "clearFirst": clear_first})
        if editor_action and editor_action in self._EDITOR_ACTION_KEYS:
            time.sleep(0.3)
            self.press_key(self._EDITOR_ACTION_KEYS[editor_action])
        return result

    def tap_and_type(self, x: int, y: int, text: str, clear_first: bool = True, editor_action: Optional[str] = None):
        """原子化 tap+type+editorAction，走 Bridge 服务端一次完成。"""
        payload = {"x": x, "y": y, "text": text, "clearFirst": clear_first}
        if editor_action:
            payload["editorAction"] = editor_action
        try:
            return self._post("/tap_and_type", payload)
        except Exception:
            self.tap(x, y)
            time.sleep(0.8)
            return self.type_text(text, clear_first=clear_first, editor_action=editor_action)

    # ── 导航操作 ──────────────────────────────────────────────────────────────

    def scroll_down(self):
        """向下滑动"""
        return self._post("/swipe", {"direction": "down"})

    def scroll_up(self):
        """向上滑动"""
        return self._post("/swipe", {"direction": "up"})

    def swipe(self, direction: str, distance: str = "medium"):
        """通用滑动：up/down/left/right，distance: short/medium/long"""
        return self._post("/swipe", {"direction": direction, "distance": distance})

    def back(self):
        """按返回键"""
        return self._post("/press_key", {"key": "back"})

    def home(self):
        """按 Home 键"""
        return self._post("/press_key", {"key": "home"})

    def open_app(self, pkg: str):
        """打开应用。先 home 确保干净状态，再启动。"""
        self.home()
        time.sleep(0.5)
        return self._post("/open_app", {"packageName": pkg})

    def press_key(self, key: str):
        """按系统键：back, home, recents, power, volume_up, volume_down, etc."""
        return self._post("/press_key", {"key": key})

    # ── Intent ─────────────────────────────────────────────────────────────────

    def send_intent(self, action: str, data_uri: str = None, extras: dict = None, package: str = None):
        """发送 Android Intent。用于深链接、系统设置跳转等。"""
        payload = {"action": action}
        if data_uri:
            payload["dataUri"] = data_uri
        if extras:
            payload["extras"] = extras
        if package:
            payload["packageOverride"] = package
        return self._post("/intent", payload)

    def wait(self, seconds: float):
        """等待指定秒数"""
        time.sleep(seconds)

    # ── 便捷方法：与 adb_* 函数签名完全一致 ─────────────────────────────────

    def adb_click(self, x, y):
        return self.tap(x, y)

    def adb_long_press(self, x, y, duration=1000):
        return self.long_press(x, y, duration)

    def adb_scroll_down(self):
        return self.scroll_down()

    def adb_scroll_up(self):
        return self.scroll_up()

    def adb_back(self):
        return self.back()

    def adb_home(self):
        return self.home()

    def adb_open_app(self, pkg):
        return self.open_app(pkg)

    def adb_type(self, x, y, text, editor_action=None):
        return self.tap_and_type(x, y, text, editor_action)

    def adb_wait(self, seconds):
        return self.wait(seconds)

    # ── Overlay ───────────────────────────────────────────────────────────────

    def overlay(self, text: str):
        """在手机 overlay 上显示文本。传 None 清除。"""
        return self._post("/overlay", {"text": text})

    def overlay_dashboard(self, *, text: str = None,
                          goal: str = None, step: int = None, max_steps: int = None,
                          status: str = None, elapsed: int = None, model: str = None,
                          plan: list = None, plan_state: list = None, focus_idx: int = None,
                          thinking: str = None, current_target: str = None,
                          last_action_success: bool = None, last_reflection: str = None,
                          last_mission_complete: bool = None, last_mission_reason: str = None,
                          last_verify: str = None,
                          progress: str = None, scratchpad: list = None,
                          profile: dict = None):
        """发送结构化 dashboard 数据到 overlay，所有字段可选。"""
        payload = {}
        if text is not None: payload["text"] = text
        if goal is not None: payload["goal"] = goal
        if step is not None: payload["step"] = step
        if max_steps is not None: payload["maxSteps"] = max_steps
        if status is not None: payload["status"] = status
        if elapsed is not None: payload["elapsed"] = elapsed
        if model is not None: payload["model"] = model
        if plan is not None: payload["plan"] = plan
        if plan_state is not None: payload["planState"] = plan_state
        if focus_idx is not None: payload["focusIdx"] = focus_idx
        if thinking is not None: payload["thinking"] = thinking
        if current_target is not None: payload["currentTarget"] = current_target
        if last_action_success is not None: payload["lastActionSuccess"] = last_action_success
        if last_reflection is not None: payload["lastReflection"] = last_reflection
        if last_mission_complete is not None: payload["lastMissionComplete"] = last_mission_complete
        if last_mission_reason is not None: payload["lastMissionReason"] = last_mission_reason
        if last_verify is not None: payload["lastVerify"] = last_verify
        if progress is not None: payload["progress"] = progress
        if scratchpad is not None: payload["scratchpad"] = scratchpad
        if profile is not None: payload["profile"] = profile
        return self._post("/overlay", payload)

    def overlay_clear(self):
        """清除 overlay 内容"""
        return self._post("/overlay", {"text": None})

    def overlay_reset(self):
        """重置 overlay 的所有状态和消息历史"""
        return self._delete("/overlay")

    # ── Events & Chat ─────────────────────────────────────────────────────────

    def poll_events(self, since: int = 0, limit: int = 50) -> dict:
        """Poll events from Bridge event store"""
        return self._get(f"/events?since={since}&limit={limit}")

    def send_chat_message(self, role: str, text: str, is_markdown: bool = True):
        """Send a message to the Android Chat UI"""
        return self._post("/chat", {"role": role, "text": text, "isMarkdown": is_markdown})

    # ── 语音 ──────────────────────────────────────────────────────────────────

    def voice_start(self):
        """开始语音识别（结果通过 relay WebSocket 推送）"""
        return self._post("/voice_start", {})

    def voice_stop(self):
        """停止语音识别"""
        return self._post("/voice_stop", {})

    # ── TTS ───────────────────────────────────────────────────────────────────

    def speak(self, text: str, queue: int = 1):
        """文字转语音朗读"""
        return self._post("/speak", {"text": text, "queue": queue})

    def stop_speaking(self):
        """停止朗读"""
        return self._post("/stop_speaking", {})
