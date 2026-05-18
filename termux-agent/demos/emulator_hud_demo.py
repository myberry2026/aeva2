import time
import sys
import select
import subprocess
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console
from rich.table import Table

console = Console()

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

def phone_notify(msg):
    """在手机通知栏显示 Agent 的想法"""
    run_adb(["shell", "cmd", "notification", "post", "-p", "com.android.shell", "-S", "bigtext", "-t", "🧠 Agent Thought", "Agent", msg])

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
        self.thought = "准备演示..."
        self.current_action = "等待启动"
        self.action_history = []
        self.layout = make_layout()

    def update_display(self, thought, action, status_msg=None):
        self.thought = thought
        if action and "🤔" not in action:
            self.action_history.append(f"[Step {self.step}] {action}")
        
        # Header
        self.layout["header"].update(Panel(f"[bold cyan]Emulator HUD Demo[/bold cyan] | [yellow]目标: 演示真机联动 + 插嘴机制[/yellow]", border_style="blue"))
        
        # Thought Panel
        self.layout["thought"].update(Panel(f"[bold white]Step {self.step} Thought:[/bold white]\n\n{self.thought}", title="🧠 Agent's Mind", border_style="green"))
        
        # Actions Panel
        action_table = Table(show_header=False, expand=True, box=None)
        for h in self.action_history[-8:]:
            action_table.add_row(h)
        self.layout["actions"].update(Panel(action_table, title="📜 History", border_style="magenta"))
        
        # Footer
        footer_text = status_msg or f"当前动作: {action}"
        self.layout["footer"].update(Panel(f"[bold blink red]●[/bold blink red] {footer_text} | [white]按回车插嘴[/white]", border_style="red"))

def run_emulator_demo():
    hud = AgentHUD()
    
    # 模拟一系列在模拟器上执行的动作
    demo_steps = [
        {
            "thought": "我发现现在可能不在主屏幕，为了安全起见，我先执行 HOME 回到桌面。",
            "action": "ADB HOME",
            "cmd": ["shell", "input", "keyevent", "3"]
        },
        {
            "thought": "现在已经在桌面了，我准备打开系统的‘设置’应用来看看设备信息。",
            "action": "Open Settings",
            "cmd": ["shell", "am", "start", "-a", "android.settings.SETTINGS"]
        },
        {
            "thought": "设置已打开。为了演示滚动效果，我准备向下滑动屏幕。",
            "action": "Scroll Down",
            "cmd": ["shell", "input", "swipe", "500", "1500", "500", "500", "500"]
        },
        {
            "thought": "演示任务即将完成，我现在最后按一次 BACK 键返回。",
            "action": "ADB BACK",
            "cmd": ["shell", "input", "keyevent", "4"]
        }
    ]

    with Live(hud.layout, refresh_per_second=4, screen=True) as live:
        for step in demo_steps:
            # 1. 更新 Thought 并在手机发通知
            hud.update_display(step["thought"], "🤔 决策中...")
            phone_notify(step["thought"])
            time.sleep(1.5)
            
            # 2. 拦截窗口 (3秒倒计时)
            is_interrupted = False
            for i in range(3, 0, -1):
                status = f"即将执行: [bold yellow]{step['action']}[/bold yellow] ({i}s) [按回车插嘴]"
                hud.update_display(step["thought"], "🤔 决策中...", status_msg=status)
                
                ir, _, _ = select.select([sys.stdin], [], [], 1.0)
                if ir:
                    sys.stdin.readline() # 清空回车
                    hud.update_display(step["thought"], "[bold red]🚫 已被拦截！[/bold red]")
                    live.stop()
                    console.print("\n" + "═"*50, style="bold red")
                    user_hint = console.input("[bold yellow][Boss 指令]: [/bold yellow]")
                    console.print("═"*50 + "\n", style="bold red")
                    
                    # 模拟根据用户指令改变想法
                    hud.thought = f"[已接收老板指令]: {user_hint}\n[模拟回复]: 收到，我将取消原定的 {step['action']}，改为响应您的指令。"
                    phone_notify(f"Boss says: {user_hint}")
                    is_interrupted = True
                    live.start()
                    time.sleep(2)
                    break
            
            if is_interrupted:
                hud.step += 1
                continue # 跳过当前预定动作
                
            # 3. 正常执行 ADB 动作
            hud.update_display(step["thought"], f"🚀 正在执行: {step['action']}")
            run_adb(step["cmd"])
            time.sleep(1.5)
            hud.step += 1

    console.print("\n[bold green]模拟器 HUD 联动演示结束！[/bold green]")

if __name__ == "__main__":
    try:
        # 确保 ADB 已连接
        res = run_adb(["devices"])
        if "device\n" not in res.stdout:
            print("错误: 未检测到已连接的模拟器/真机，请先启动 ADB。")
        else:
            run_emulator_demo()
    except KeyboardInterrupt:
        pass
