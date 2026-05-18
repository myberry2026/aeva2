"""
Terminal Dashboard for humanoid_agent.

独立进程，作为 WS client 连接 agent，实时显示：
- 顶部：目标 / Step / Status / Elapsed / Model
- 左：Plan checklist
- 右：Scratchpad（含用户插话高亮）
- 底部：Last thought / Last verify / Profile 摘要

跑法：
    pip install rich websockets
    python dashboard_tui.py

切到另一个终端跑 agent，dashboard 自动同步。
"""
import asyncio
import json
import os
import sys

try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.console import Group
    from rich import box
except ImportError:
    print("请先装 rich: pip install rich")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("请先装 websockets: pip install websockets")
    sys.exit(1)

WS_URL = os.getenv("WS_URL", "ws://localhost:8765")

# 全局 state（dashboard 内部副本，跟 agent broadcast 同步）
_state = {
    "goal": "(等待 agent 启动...)",
    "step": 0,
    "max_steps": 15,
    "status": "WAITING",
    "elapsed": 0,
    "model": "?",
    "plan": [],
    "plan_state": [],
    "focus_idx": -1,
    "scratchpad": [],
    "last_thought": "",
    "last_verify": "",
    "current_target": "",
    "last_action_success": None,
    "last_reflection": "",
    "last_mission_complete": None,
    "last_mission_reason": "",
    "last_progress": "",
    "profile": {},
}
# 等待 agent 确认前的"用户已发但 agent 还没处理"输入队列（立即可见）
_pending_user_inputs = []  # list of str


def _make_header():
    s = _state
    status = s.get("status", "?")
    status_color = (
        "green" if status.startswith("SUCCESS")
        else "red" if status in ("STEPS_EXHAUSTED", "FAILED")
        else "yellow" if status == "WAITING"
        else "cyan"
    )
    goal_short = s["goal"] if len(s["goal"]) < 80 else s["goal"][:77] + "..."
    line1 = Text(f"🎯 {goal_short}", style="bold white")
    line2 = Text.assemble(
        ("Step ", "dim"),
        (f"{s['step']}/{s['max_steps']}", "bold"),
        " │ ",
        ("Status: ", "dim"),
        (status, f"bold {status_color}"),
        " │ ",
        ("Elapsed: ", "dim"),
        (f"{s['elapsed']}s", "bold"),
        " │ ",
        ("Model: ", "dim"),
        (s.get("model", "?"), "bold magenta"),
    )
    return Panel(Group(line1, line2), border_style="cyan", box=box.HEAVY)


def _make_plan():
    s = _state
    plan = s.get("plan", [])
    plan_state = s.get("plan_state", [])
    focus = s.get("focus_idx", -1)
    done_count = sum(plan_state)
    if not plan:
        body = Text("（未生成 Plan）", style="dim italic")
    else:
        t = Table.grid(padding=(0, 1))
        for i, task in enumerate(plan):
            done = plan_state[i] if i < len(plan_state) else False
            if done:
                marker, style = "✅", "green"
            elif i == focus:
                marker, style = "👉", "bold yellow"
            else:
                marker, style = "⏳", "dim"
            label = task if len(task) < 50 else task[:47] + "..."
            t.add_row(Text(marker), Text(f"{i+1}. {label}", style=style))
        body = t
    title = f"📋 Plan [{done_count}/{len(plan)} done]" if plan else "📋 Plan"
    return Panel(body, title=title, border_style="blue")


def _make_scratchpad():
    s = _state
    scratchpad = s.get("scratchpad", [])
    t = Table.grid(padding=(0, 1))
    # 先放 pending user input（agent 还没处理的，提醒用户已收到）
    for pending in _pending_user_inputs:
        t.add_row(Text("⏳🎤", style="bold yellow"),
                  Text(f"[等待 agent 处理] {pending}", style="bold yellow"))
    # 再放 scratchpad 内容
    for note in scratchpad[-12:]:  # 最近 12 条
        if "USER 插话" in note or "[USER" in note:
            t.add_row(Text("🎤", style="bold red"), Text(note, style="bold red"))
        else:
            t.add_row(Text("•", style="cyan"),
                      Text(note[:90] + ("..." if len(note) > 90 else ""), style="white"))
    if not scratchpad and not _pending_user_inputs:
        body = Text("（暂无记录）", style="dim italic")
    else:
        body = t
    title = f"📝 Scratchpad ({len(scratchpad)}{'  +' + str(len(_pending_user_inputs)) + ' pending' if _pending_user_inputs else ''})"
    return Panel(body, title=title, border_style="green")


def _make_reflection():
    s = _state
    thought = s.get("last_thought", "").strip() or "(no thought yet)"
    target = s.get("current_target", "")
    action_success = s.get("last_action_success")
    reflection = s.get("last_reflection", "").strip()
    mission_complete = s.get("last_mission_complete")
    mission_reason = s.get("last_mission_reason", "").strip()
    progress = s.get("last_progress", "").strip()

    def bool_icon(b):
        if b is True: return Text("✓", style="bold green")
        if b is False: return Text("✗", style="bold red")
        return Text("·", style="dim")

    lines = []
    # Action 正在做啥
    if target:
        lines.append(Text.assemble(("⚡ Action: ", "bold cyan"), (target, "yellow")))
    # Thought 完整展开（多行也 OK）
    lines.append(Text.assemble(("🤔 Thought: ", "bold cyan"), (thought, "white")))
    # 分行展示 verify 子字段
    if action_success is not None:
        lines.append(Text.assemble(
            ("✓ Action: ", "bold cyan"),
            bool_icon(action_success),
            ("  ", ""),
            (reflection or "(no reflection)", "white"),
        ))
    if mission_complete is not None:
        lines.append(Text.assemble(
            ("🏁 Mission: ", "bold cyan"),
            bool_icon(mission_complete),
            ("  ", ""),
            (mission_reason or "(no reason)", "white"),
        ))
    if progress:
        lines.append(Text.assemble(("📈 Progress: ", "bold cyan"), (progress, "green")))

    return Panel(Group(*lines), title="🧠 Agent thinking", border_style="magenta", box=box.SIMPLE)


def _make_profile():
    s = _state
    p = s.get("profile", {})
    if not p:
        return Panel(Text("(no profile data)", style="dim italic"), border_style="dim")
    wall = p.get("wall", 0)
    profiled = p.get("profiled", 0)
    llm = p.get("llm", 0)
    in_tok = p.get("in_tok", 0)
    out_tok = p.get("out_tok", 0)
    line = Text.assemble(
        ("⏱️  ", ""),
        (f"{wall}s ", "bold"), ("wall │ ", "dim"),
        (f"{profiled}s ", "cyan"), ("profiled │ ", "dim"),
        (f"{llm}s ", "yellow"), ("LLM  ", "dim"),
        ("│  🪙 ", ""),
        (f"in {in_tok:,} ", "green"), ("/ ", "dim"),
        (f"out {out_tok:,}", "red"),
    )
    return Panel(line, border_style="dim", box=box.SIMPLE)


def build_layout():
    layout = Layout()
    layout.split_column(
        Layout(_make_header(), name="header", size=5),
        Layout(name="body"),
        Layout(_make_reflection(), name="reflection", size=10),  # 加高放更多 verify 字段
        Layout(_make_profile(), name="profile", size=3),
    )
    layout["body"].split_row(
        Layout(_make_plan(), name="plan"),
        Layout(_make_scratchpad(), name="scratchpad"),
    )
    return layout


async def listen_ws():
    global _state
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue
                    t = msg.get("type")
                    if t == "state":
                        _state.update(msg)
                        # 当 scratchpad 已经有该 pending 内容（说明 agent 处理了），从 pending 移除
                        sp_joined = " ".join(_state.get("scratchpad", []))
                        _pending_user_inputs[:] = [
                            p for p in _pending_user_inputs if p not in sp_joined
                        ]
                    elif t == "event" and msg.get("kind") == "user_input_pending":
                        text = msg.get("text", "")
                        if text and text not in _pending_user_inputs:
                            _pending_user_inputs.append(text)
                    elif t == "event" and msg.get("kind") == "user_input":
                        # 兼容旧 event name（agent 自己也广播这个）
                        pass
        except (ConnectionRefusedError, OSError, websockets.exceptions.ConnectionClosed):
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[dashboard] WS error: {e}")
            await asyncio.sleep(1)


async def main():
    listener = asyncio.create_task(listen_ws())
    with Live(build_layout(), refresh_per_second=4, screen=True) as live:
        try:
            while True:
                live.update(build_layout())
                await asyncio.sleep(0.25)
        except KeyboardInterrupt:
            pass
    listener.cancel()


if __name__ == "__main__":
    print(f"[dashboard] 连接 {WS_URL}...")
    print("[dashboard] Ctrl+C 退出。")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[dashboard] bye")
