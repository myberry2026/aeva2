"""
output_channel.py — 统一输出接口，overlay / dashboard / both 三种模式。

用法:
    from output_channel import create_output
    out = create_output("overlay", bridge_client=hc)
    out.send_state("🎯 goal", snapshot_dict)
    out.send_event({"type": "event", "kind": "user_input", ...})
"""
from abc import ABC, abstractmethod


class OutputBackend(ABC):
    """单个输出后端的接口。"""

    @abstractmethod
    def send_state(self, text: str, snapshot: dict):
        """发送状态更新（overlay 文本 + 结构化 snapshot）。"""
        ...

    @abstractmethod
    def send_event(self, event: dict):
        """发送瞬时事件（用户插话等）。"""
        ...

    @abstractmethod
    def reset(self):
        """重置后端状态。"""
        ...

    def start(self):
        """初始化后端（如启 WS server）。默认 no-op。"""
        pass

    def stop(self):
        """关闭后端。默认 no-op。"""
        pass


class OverlayBackend(OutputBackend):
    """发送到手机 overlay（通过 bridge HTTP API）。"""

    def __init__(self, bridge_client):
        self._bc = bridge_client

    def send_state(self, text: str, snapshot: dict):
        fields = self._snapshot_to_fields(snapshot)
        self._bc.overlay_dashboard(text=text, **fields)

    def send_event(self, event: dict):
        # overlay 不需要瞬时事件
        pass

    def reset(self):
        """重置 overlay 的所有状态和消息历史"""
        self._bc.overlay_reset()

    @staticmethod
    def _snapshot_to_fields(s: dict) -> dict:
        """将 _snapshot_state() 的 dict 转为 overlay_dashboard 的 kwargs。"""
        s = dict(s)
        s.pop("type", None)
        fields = {}
        fields["goal"] = s.get("goal")
        fields["step"] = s.get("step")
        fields["max_steps"] = s.get("max_steps")
        fields["status"] = s.get("status")
        fields["elapsed"] = s.get("elapsed")
        fields["model"] = s.get("model")
        fields["plan"] = s.get("plan")
        fields["plan_state"] = s.get("plan_state")
        fields["focus_idx"] = s.get("focus_idx")
        fields["thinking"] = s.get("last_thought")
        fields["current_target"] = s.get("current_target")
        fields["last_action_success"] = s.get("last_action_success")
        fields["last_reflection"] = s.get("last_reflection")
        fields["last_mission_complete"] = s.get("last_mission_complete")
        fields["last_mission_reason"] = s.get("last_mission_reason")
        fields["last_verify"] = s.get("last_verify")
        fields["progress"] = s.get("last_progress")
        fields["scratchpad"] = s.get("scratchpad")
        fields["profile"] = s.get("profile")
        return {k: v for k, v in fields.items() if v is not None}


class DashboardBackend(OutputBackend):
    """发送到终端 Dashboard TUI（通过 WebSocket）。"""

    def __init__(self, ws_port: int = 8768):
        self._ws_port = ws_port

    def send_state(self, text: str, snapshot: dict):
        from ws_channel import ws_broadcast
        ws_broadcast(snapshot)

    def send_event(self, event: dict):
        from ws_channel import ws_broadcast
        ws_broadcast(event)

    def reset(self):
        # dashboard 目前不处理重置，或者发一个空状态
        pass

    def start(self):
        from ws_channel import start_ws_server
        start_ws_server(port=self._ws_port)

    def stop(self):
        pass


class CompositeBackend(OutputBackend):
    """同时发送到多个后端。"""

    def __init__(self, backends: list):
        self._backends = backends

    def send_state(self, text: str, snapshot: dict):
        for b in self._backends:
            try:
                b.send_state(text, snapshot)
            except Exception:
                pass

    def send_event(self, event: dict):
        for b in self._backends:
            try:
                b.send_event(event)
            except Exception:
                pass

    def reset(self):
        for b in self._backends:
            try:
                b.reset()
            except Exception:
                pass

    def start(self):
        for b in self._backends:
            try:
                b.start()
            except Exception:
                pass

    def stop(self):
        for b in self._backends:
            try:
                b.stop()
            except Exception:
                pass


def create_output(target: str, bridge_client=None, ws_port: int = 8768) -> OutputBackend:
    """
    创建输出后端。

    Args:
        target: "overlay" / "dashboard" / "both"
        bridge_client: BridgeClient 实例（overlay 模式需要）
        ws_port: WebSocket 端口（dashboard 模式需要）
    """
    backends = []
    if target in ("overlay", "both"):
        if bridge_client is not None:
            backends.append(OverlayBackend(bridge_client))
    if target in ("dashboard", "both"):
        backends.append(DashboardBackend(ws_port))

    if len(backends) == 1:
        return backends[0]
    return CompositeBackend(backends)
