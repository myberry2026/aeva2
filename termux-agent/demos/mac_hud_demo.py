import time
import sys
import select
import os
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console
from rich.table import Table

console = Console()

def mac_notify(msg):
    """显示 Mac 通知并语音播报"""
    safe_msg = msg.replace('"', '\"').replace("'", "")
    # 语音播报：绝对不会错过
    os.system(f'say "Agent thinking: {safe_msg[:60]}" &')
    # 通知弹窗
    script = f'display notification "{safe_msg}" with title "🤖 Agent" subtitle "Step {hud_state["step"]}"'
    os.system(f"osascript -e '{script}'")

def mac_boss_interrupt(action_desc):
    """弹出真正的 Mac 对话框进行拦截"""
    title = "Boss 拦截时刻"
    prompt = f"Agent 即将执行: {action_desc}\\n\\n请输入您的指令（直接取消则继续执行）:"
    script = f'display dialog "{prompt}" default answer "" with title "{title}" buttons {{"取消", "下达指令"}} default button "下达指令"'
    # 这里我们还是在终端输入比较好，Dialog 会阻塞 Python 进程
    # 但我们可以用弹窗作为视觉提醒
    os.system(f'osascript -e \'display notification "老板请插嘴！" with title "🚫 已拦截"\' &')

# 全局状态，方便通知函数读取
hud_state = {"step": 1}

def make_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3)
    )
    layout["main"].split_row(
        Layout(name="thought", ratio=2),
        Layout(name="actions", ratio=1)
    )
    return layout

class AgentHUD:
    def __init__(self):
        self.step = 1
        self.thought = "准备中..."
        self.current_action = "等待启动"
        self.action_history = []
        self.layout = make_layout()

    def update_display(self, thought, action, status_msg=None):
        if thought: self.thought = thought
        hud_state["step"] = self.step
        
        if action and "🤔" not in action:
            self.action_history.append(f"[Step {self.step}] {action}")
        
        # Header
        self.layout["header"].update(Panel(f"[bold cyan]Agent HUD Mac v2.0[/bold cyan] | [yellow]实时进度同步演示[/yellow]", border_style="blue"))
        
        # Thought Panel (核心：确保文字显式渲染)
        content = f"[bold green]▶ 思考内容:[/bold green]\n\n[white]{self.thought}[/white]"
        self.layout["thought"].update(Panel(content, title=f"🧠 Step {self.step} Mind", border_style="green", padding=(1, 2)))
        
        # Actions Panel
        action_table = Table(show_header=False, expand=True, box=None)
        for h in self.action_history[-10:]:
            action_table.add_row(h)
        self.layout["actions"].update(Panel(action_table, title="📜 History", border_style="magenta"))
        
        # Footer
        footer_text = status_msg or f"当前状态: {action}"
        self.layout["footer"].update(Panel(f"[bold blink red]●[/bold blink red] {footer_text}", border_style="red"))

def run_mac_demo():
    hud = AgentHUD()
    
    # 模拟一套全自动任务流 (使用极其逼真的 LLM 思考逻辑)
    demo_steps = [
        {
            "thought": "当前屏幕为手机桌面。根据总目标要求发送短信给 '12345'。可交互清单中发现 ID 12 是短信应用的图标 (content-desc: 'Messages')。我需要使用 click 动作打开短信应用。",
            "action": "Click ID: 12 (Messages)"
        },
        {
            "thought": "已进入短信应用主页。发现列表第一项 (ID 4) 的文本是 '12345'，这正是我要找的联系人。我将点击 ID 4 进入聊天会话详情页。",
            "action": "Click ID: 4 (Contact 12345)"
        },
        {
            "thought": "成功进入对话框。当前可交互清单中 ID 7 是消息输入区 (id:compose_message_text, class:EditText)。我将调用 type 命令，通过 ADBKeyBoard 注入中文字符串 '进度已同步'。",
            "action": "Type ID: 7 ('进度已同步')"
        },
        {
            "thought": "消息已成功输入。界面右侧出现了一个纸飞机图标 (ID 9, desc: 'Send SMS')。这是最终的发送动作。点击它将完成整个任务的实质性操作。",
            "action": "Click ID: 9 (Send SMS)"
        },
        {
            "thought": "核验完成：消息气泡已出现在屏幕中央，且带有时间戳。对照【总目标】，所有子任务均已完成，Gap 为 None。果断执行 finish 宣告任务结束。",
            "action": "Finish Task (Mission Complete)"
        }
    ]

    with Live(hud.layout, refresh_per_second=4, screen=True) as live:
        for step in demo_steps:
            # 1. 同步思想 (Mac 弹窗)
            hud.update_display(step["thought"], "🤔 深度分析中...")
            mac_notify(step["thought"])
            time.sleep(2.0)
            
            # 2. 拦截窗口 (3秒倒计时)
            is_interrupted = False
            for i in range(3, 0, -1):
                status = f"即将执行: [bold yellow]{step['action']}[/bold yellow] ({i}s) [按回车拦截]"
                hud.update_display(step["thought"], "🤔 深度分析中...", status_msg=status)
                
                # 监听键盘
                ir, _, _ = select.select([sys.stdin], [], [], 1.0)
                if ir:
                    sys.stdin.readline()
                    hud.update_display(step["thought"], "[bold red]🚫 流程已被强行挂起！[/bold red]")
                    mac_boss_interrupt(step['action'])
                    live.stop()
                    console.print("\n" + "═"*50, style="bold red")
                    user_hint = console.input("[bold yellow][Boss 指令 (如: '不要发这句，改发xxx')]: [/bold yellow]")
                    console.print("═"*50 + "\n", style="bold red")
                    
                    # 模拟响应老板指令
                    hud.thought = f"[最高优先级指令]: {user_hint}\n[重新决策]: 收到指令，已放弃 {step['action']}，正在依据新指令重新生成 Plan 和动作坐标..."
                    mac_notify("已切断原逻辑，正在执行您的指令。")
                    is_interrupted = True
                    live.start()
                    time.sleep(3.0)
                    break
            
            if is_interrupted:
                hud.step += 1
                continue
                
            # 3. 模拟执行
            hud.update_display(step["thought"], f"🚀 调用 ADB 执行: {step['action']}")
            time.sleep(2.0)
            hud.step += 1

    console.print("\n[bold green]Mac 桌面 HUD 深度演示结束！[/bold green]")

if __name__ == "__main__":
    try:
        run_mac_demo()
    except KeyboardInterrupt:
        pass
