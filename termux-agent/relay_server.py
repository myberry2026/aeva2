"""
relay_server.py — 极简 HTTP 守护进程：接收 /task 指令，spawn agent。

在手机 Termux 上作为长期运行 Daemon:
  python relay_server.py

Android App 通过 HTTP POST /task 触发 agent:
  POST http://localhost:8767/task  {"text": "帮我设个闹钟"}

不再需要 WebSocket / RelayClient / ws_channel 中间层。
"""
import json
import subprocess
import os
import signal
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

LISTEN_PORT = int(os.getenv("RELAY_PORT", "8767"))
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="[relay] %(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("relay")

# --- Agent 进程管理 ---
_agent_proc = None


def _is_agent_alive():
    global _agent_proc
    if _agent_proc is None:
        return False
    ret = _agent_proc.poll()
    if ret is not None:
        log.info(f"Agent 进程已结束 (exit code: {ret})")
        _agent_proc = None
        return False
    return True


def spawn_agent(goal_text: str):
    """启动新的 agent 进程。如果已有 agent 在跑，先杀掉。"""
    global _agent_proc

    if _is_agent_alive():
        log.info("🔄 Agent 正在运行，先终止旧进程...")
        _agent_proc.send_signal(signal.SIGTERM)
        try:
            _agent_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _agent_proc.kill()
        _agent_proc = None

    log.info(f"🚀 启动 Agent: {goal_text[:60]}...")
    agent_script = os.path.join(PROJECT_DIR, "scripts", "start_agent_termux.sh")
    log_dir = os.path.join(PROJECT_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = open(os.path.join(log_dir, "agent_latest.log"), "a")
    _agent_proc = subprocess.Popen(
        ["bash", agent_script, goal_text],
        cwd=PROJECT_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    log.info(f"✅ Agent PID: {_agent_proc.pid}")


class RelayHandler(BaseHTTPRequestHandler):
    """极简 HTTP handler：只处理 /task 和 /status。"""

    def do_POST(self):
        if self.path == "/task":
            self._handle_task()
        elif self.path == "/stop":
            self._handle_stop()
        else:
            self._reply(404, {"error": f"Unknown path: {self.path}"})

    def do_GET(self):
        if self.path == "/status":
            self._handle_status()
        elif self.path == "/health":
            self._reply(200, {"status": "ok"})
        else:
            self._reply(404, {"error": f"Unknown path: {self.path}"})

    def _handle_task(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
        except Exception as e:
            self._reply(400, {"error": f"Bad JSON: {e}"})
            return

        text = body.get("text", "").strip()
        if not text:
            self._reply(400, {"error": "Missing 'text' field"})
            return

        log.info(f"📥 收到任务: {text[:60]}...")
        
        # 优化：在后台线程启动 Agent，避免阻塞 HTTP 响应导致 App 超时
        import threading
        threading.Thread(target=spawn_agent, args=(text,), daemon=True).start()
        
        self._reply(200, {
            "status": "ok",
            "message": "Agent spawn initiated in background",
        })

    def _handle_status(self):
        alive = _is_agent_alive()
        pid = _agent_proc.pid if _agent_proc else None
        log.info(f"📊 Status check: alive={alive}, pid={pid}")
        self._reply(200, {
            "agent_running": alive,
            "pid": pid,
        })

    def _handle_stop(self):
        global _agent_proc
        if _agent_proc is None:
            self._reply(200, {"status": "ok", "message": "No agent running"})
            return
            
        pid = _agent_proc.pid
        log.info(f"🛑 Stopping agent (PID: {pid})...")
        
        def kill_process(proc):
            global _agent_proc
            try:
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    log.info(f"SIGTERM timeout, sending SIGKILL to {pid}")
                    proc.kill()
                log.info(f"✅ Agent stopped")
            except Exception as e:
                log.error(f"Failed to stop agent: {e}")
            finally:
                if _agent_proc == proc:
                    _agent_proc = None

        import threading
        threading.Thread(target=kill_process, args=(_agent_proc,), daemon=True).start()
        self._reply(200, {"status": "ok", "message": f"Agent (PID: {pid}) stopping"})

    def _reply(self, code, data):
        response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)

    def log_message(self, format, *args):
        # 用 logging 代替默认的 stderr 输出
        log.info(f"HTTP {args[0]}")


def main():
    log.info("=" * 45)
    log.info(f"🚀 Relay HTTP Server 启动 (端口: {LISTEN_PORT})")
    log.info(f"   POST /task  — 提交任务")
    log.info(f"   GET  /status — 查询 Agent 状态")
    log.info("=" * 45)

    server = HTTPServer(("0.0.0.0", LISTEN_PORT), RelayHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("已退出。")
        server.server_close()


if __name__ == "__main__":
    main()
