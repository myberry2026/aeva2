"""
WebSocket 用户输入通道（agent 用户中断 / 状态广播）。

后台线程跑 asyncio event loop，主线程通过 queue 收发消息。
不强依赖 websockets 库——装了就启 server，没装就 graceful no-op。

接口（agent 主程序需要的全部）：
    start_ws_server(port=8765) -> bool
        启动后台 server。已启动或装失败返回 False。
    ws_poll() -> dict | None
        非阻塞拉一条客户端发来的消息。无消息返回 None。
    ws_broadcast(data: dict) -> None
        从主线程广播 JSON 给所有客户端（错误吞掉，非阻塞）。
"""
import asyncio
import json
import queue
import threading

try:
    import websockets
    _WS_AVAILABLE = True
    DEFAULT_PORT = 8768
except ImportError:
    _WS_AVAILABLE = False

_inbox = queue.Queue()       # 主线程消费：用户发来的命令/插话
_relay_inbox = queue.Queue() # relay 语音事件队列
_clients = set()             # 当前连入的 WS 客户端集合
_loop = None                 # 后台线程的 asyncio loop 引用，给 broadcast 用
_started = False

async def _handler(ws):
    _clients.add(ws)
    print(f"[ws] 🔌 client connected (total {len(_clients)})")
    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except Exception:
                data = {"type": "text", "text": str(raw)}
            _inbox.put(data)
            # 立刻 echo 给所有其他客户端（dashboard 立即可见用户输入，不等 agent 处理）
            text = data.get("text") or data.get("msg") or ""
            if text:
                echo = json.dumps({
                    "type": "event",
                    "kind": "user_input_pending",
                    "text": text,
                }, ensure_ascii=False)
                for client in list(_clients):
                    if client is ws:
                        continue  # 不回声给发送者
                    try:
                        await client.send(echo)
                    except Exception:
                        pass
    finally:
        _clients.discard(ws)
        print(f"[ws] 🔌 client disconnected (remaining {len(_clients)})")

async def _serve(port):
    global _loop
    _loop = asyncio.get_event_loop()
    async with websockets.serve(_handler, "127.0.0.1", port):
        await asyncio.Future()  # run forever

def start_ws_server(port=8765):
    """在后台线程启动 WebSocket server。"""
    global _started
    if _started:
        return True
    if not _WS_AVAILABLE:
        print("[ws] ⚠️ websockets 未装，跳过 server（pip install websockets）")
        return False

    def _runner():
        asyncio.run(_serve(port))

    threading.Thread(target=_runner, daemon=True, name="ws-server").start()
    _started = True
    print(f"[ws] 🚀 server on ws://localhost:{port}")
    return True

def ws_poll():
    """非阻塞拿一条用户消息。无返回 None。"""
    try:
        return _inbox.get_nowait()
    except queue.Empty:
        return None

def ws_broadcast(data):
    """从主线程广播 JSON 给所有 WS 客户端（非阻塞，错误吞掉）。"""
    if not _clients or not _loop:
        return
    msg = json.dumps(data, ensure_ascii=False)
    for client in list(_clients):
        try:
            asyncio.run_coroutine_threadsafe(client.send(msg), _loop)
        except Exception:
            pass
