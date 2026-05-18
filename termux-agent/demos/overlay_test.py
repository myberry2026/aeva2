import time
import sys
import select
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn

console = Console()

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
        self.thought = "初始化中..."
        self.current_action = "等待输入"
        self.action_history = []
        self.layout = make_layout()

    def update_display(self, thought, action):
        self.thought = thought
        self.current_action = action
        if action:
            self.action_history.append(f"[Step {self.step}] {action}")
        
        # Header
        self.layout["header"].update(Panel(f"[bold cyan]Agent HUD Prototype v1.0[/bold cyan] | [yellow]Goal: 演示插嘴机制[/yellow]", border_style="blue"))
        
        # Thought Panel
        self.layout["thought"].update(Panel(f"[bold white]Step {self.step} Thought:[/bold white]\n\n{self.thought}", title="🧠 Agent's Mind", border_style="green"))
        
        # Actions Panel
        action_table = Table(show_header=False, expand=True, box=None)
        for h in self.action_history[-8:]: # 只显示最近8条
            action_table.add_row(h)
        self.layout["actions"].update(Panel(action_table, title="📜 History", border_style="magenta"))
        
        # Footer
        self.layout["footer"].update(Panel(f"[bold blink red]●[/bold blink red] Current Action: {self.current_action} | [white]按回车键拦截/插嘴[/white]", border_style="red"))

def run_demo():
    hud = AgentHUD()
    
    steps_data = [
        {"thought": "我正在检查手机主屏幕，寻找短信图标。看到坐标 [100, 200] 有个类似信息的消息。准备点击它。", "action": "Click [100, 200]"},
        {"thought": "已经进入短信 App。列表里有 12345 的会话。我现在需要点击它进入对话页。", "action": "Click Contact '12345'"},
        {"thought": "到达对话页面。输入框就在底部。根据之前的经验，我应该使用 ADBKeyBoard 快速输入中文消息。", "action": "Type: '老板，这招真灵'"},
        {"thought": "消息已输入，现在寻找那个蓝色的发送按钮。坐标大约在 [950, 1400] 附近。", "action": "Click Send Button"},
    ]

    with Live(hud.layout, refresh_per_second=4, screen=True) as live:
        for data in steps_data:
            hud.update_display(data["thought"], "🤔 思考中...")
            time.sleep(1.5)
            
            # 模拟决策完成，进入拦截窗口
            countdown_seconds = 3
            for i in range(countdown_seconds, 0, -1):
                msg = f"即将执行: [bold yellow]{data['action']}[/bold yellow] ({i}s 后自动开始) - [inverse]按回车键插嘴[/inverse]"
                hud.update_display(data["thought"], msg)
                
                # 非阻塞监听输入
                i, o, e = select.select([sys.stdin], [], [], 1.0)
                if i:
                    sys.stdin.readline() # 清空缓冲区
                    hud.update_display(data["thought"], "[bold red]🚫 已被老板拦截！等待指令...[/bold red]")
                    live.stop()
                    print("\n" + "="*30)
                    user_hint = input("[Boss 指令]: ")
                    print("="*30 + "\n")
                    # 这里会把 user_hint 注入下一轮 Prompt
                    hud.thought = f"[已接收老板指令]: {user_hint}\n正在重新规划逻辑..."
                    hud.action_history.append(f"[USER] {user_hint}")
                    live.start()
                    time.sleep(2)
                    break 
            else:
                # 倒计时结束，正常执行
                hud.update_display(data["thought"], f"🚀 执行动作: {data['action']}")
                time.sleep(1)
            
            hud.step += 1

    console.print("\n[bold green]演示结束！[/bold green]")

if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        pass
