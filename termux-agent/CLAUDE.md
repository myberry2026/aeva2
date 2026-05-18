# phone-vision-memory

## 概述
跑在手机 Termux 上的 AI agent 系统。接收自然语言指令，自动操控手机。

## 关键文件

| 文件 | 作用 |
|------|------|
| relay_server.py | HTTP 守护进程 (端口 8767)，接收 /task /stop /status /health |
| humanoid_agent.py | 主 agent，调用 LLM 做决策，通过 bridge 控制手机 |
| scripts/start_agent_termux.sh | agent 启动脚本，设环境变量后 exec python |
| scripts/start_daemon_termux.sh | 启动 relay_server.py 守护进程 |
| scripts/run_termux_server.sh | 一键部署：rsync → adb push → 启动守护进程 |

## relay_server.py 端点

- `POST /task` {"text": "..."} — 在 daemon thread 里 spawn agent
- `POST /stop` — SIGTERM → 等 5s → SIGKILL 杀掉 agent
- `GET /status` — {"agent_running": bool, "pid": int|null}
- `GET /health` — {"status": "ok"}

## 踩过的坑

### subprocess.Popen(stdout=PIPE) 会堵
agent 的 print 输出填满 64KB pipe buffer 后阻塞。daemon thread 只 spawn 不读 pipe。
**修:** 用 `stdout=open(logfile, "a")` 写文件。

### bash 脚本要用 exec
没有 exec 时 bash fork 子进程跑 python 然后自己退出，relay 跟踪的 PID 就死了。
**修:** `exec python -u humanoid_agent.py "$@"`

### deploy_local.sh 的 curl 要在手机上执行
LLM server (8080) 在 Android app 里，Mac curl localhost 连不到。
**修:** `adb shell curl http://127.0.0.1:8080/...`

## 环境变量 (start_agent_termux.sh)

```
CONTROL_BACKEND=bridge
BRIDGE_TOKEN=9RG2VK
BRIDGE_URL=http://127.0.0.1:8765
AGENT_MODEL=WIN
GALLERY_URL=http://127.0.0.1:8080
```
