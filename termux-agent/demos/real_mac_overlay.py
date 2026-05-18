import tkinter as tk
import threading
import time
import sys
import select
import queue
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console
from rich.table import Table

console = Console()
update_queue = queue.Queue()

# --- 真正的 Mac 悬浮窗 (Overlay) ---

class MacOverlay:
    def __init__(self, root):
        self.root = root
        self.root.title("Agent HUD")
        
        # 窗口属性：无边框、置顶、半透明
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.85)
        
        # 位置：屏幕右上角
        screen_w = self.root.winfo_screenwidth()
        self.root.geometry(f"450x180+{(screen_w - 470)}+60")
        
        # 背景和文字样式
        frame = tk.Frame(self.root, bg="#1e1e1e", highlightthickness=3, highlightbackground="#00ff00")
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="🤖 AGENT HUD v2.1", fg="#00ff00", bg="#1e1e1e", font=("Arial", 14, "bold")).pack(pady=8)
        
        self.label = tk.Label(frame, text="Waiting...", fg="white", bg="#1e1e1e", font=("Arial", 11), wraplength=420, justify=tk.LEFT)
        self.label.pack(padx=15, pady=5, fill=tk.BOTH, expand=True)
        
        self.status_label = tk.Label(frame, text="READY", fg="#ffcc00", bg="#1e1e1e", font=("Arial", 10, "italic"))
        self.status_label.pack(pady=8)

        # 定时检查队列更新 UI
        self.root.after(100, self.check_queue)

    def check_queue(self):
        try:
            while True:
                msg_type, content = update_queue.get_nowait()
                if msg_type == "text":
                    self.label.config(text=content)
                elif msg_type == "status":
                    self.status_label.config(text=f"STATUS: {content}")
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

# --- TUI 仪表盘逻辑 (复用) ---

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
        self.current_action = "等待启动"
        self.action_history = []
        self.layout = make_layout()

    def update_display(self, thought, action, status_msg=None):
        if thought: 
            self.thought = thought
            update_queue.put(("text", thought))
        if action and "🤔" not in action:
            self.action_history.append(f"[Step {self.step}] {action}")
        
        self.layout["header"].update(Panel(f"[bold cyan]Agent TUI Control Panel[/bold cyan] | [yellow]实时插嘴模式开启[/yellow]", border_style="blue"))
        content = f"[bold green]▶ 思考内容:[/bold green]\n\n[white]{self.thought}[/white]"
        self.layout["thought"].update(Panel(content, title=f"🧠 Step {self.step} Mind", border_style="green", padding=(1, 2)))
        
        action_table = Table(show_header=False, expand=True, box=None)
        for h in self.action_history[-8:]:
            action_table.add_row(h)
        self.layout["actions"].update(Panel(action_table, title="📜 History", border_style="magenta"))
        
        footer_text = status_msg or f"当前动作: {action}"
        self.layout["footer"].update(Panel(f"[bold blink red]●[/bold blink red] {footer_text} | [white]按回车键拦截[/white]", border_style="red"))
        
        if status_msg:
            update_queue.put(("status", status_msg))
        else:
            update_queue.put(("status", action))

def run_agent_logic(hud):
    """在后台线程运行的 Agent 模拟逻辑"""
    demo_steps = [
        {"thought": "当前屏幕为手机桌面。我正准备点击 ID 12 (短信应用) 图标。", "action": "Click Messages"},
        {"thought": "已进入短信列表。发现目标联系人 12345 在第一行 (ID 4)。准备点击进入会话。", "action": "Click Contact 12345"},
        {"thought": "到达对话框。我将使用 ADBKeyBoard 极速注入消息：'老板，看右边！这是真正的 Overlay'。", "action": "Type Chinese Message"},
        {"thought": "核验发送结果：文字已进入气泡。点击发送按钮 (ID 9) 宣告任务达成。", "action": "Click Send Button"}
    ]

    with Live(hud.layout, refresh_per_second=4, screen=True) as live:
        for step in demo_steps:
            hud.update_display(step["thought"], "🤔 深度分析中...")
            time.sleep(2.5)
            
            # 拦截窗口
            is_interrupted = False
            for i in range(3, 0, -1):
                status = f"即将执行: [bold yellow]{step['action']}[/bold yellow] ({i}s) [按回车拦截]"
                hud.update_display(step["thought"], "🤔 准备就绪", status_msg=status)
                
                ir, _, _ = select.select([sys.stdin], [], [], 1.0)
                if ir:
                    sys.stdin.readline()
                    update_queue.put(("text", "!!! 收到老板指令，执行已强行挂起 !!!"))
                    update_queue.put(("status", "BOSS INTERRUPTED"))
                    hud.update_display(step["thought"], "[bold red]🚫 已拦截！[/bold red]")
                    live.stop()
                    console.print("\n" + "═"*50, style="bold red")
                    user_hint = console.input("[bold yellow][Boss 指令]: [/bold yellow]")
                    console.print("═"*50 + "\n", style="bold red")
                    
                    hud.thought = f"[已接收老板指令]: {user_hint}\n正在依据您的指示重新决策..."
                    update_queue.put(("text", f"BOSS SAYS: {user_hint}"))
                    is_interrupted = True
                    live.start()
                    time.sleep(3.0)
                    break
            
            if is_interrupted:
                hud.step += 1
                continue
                
            hud.update_display(step["thought"], f"🚀 正在执行: {step['action']}")
            time.sleep(2.0)
            hud.step += 1

    console.print("\n[bold green]真正的 Overlay 演示结束！[/bold green]")
    # 模拟结束退出
    time.sleep(1)
    os._exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    overlay = MacOverlay(root)
    hud = AgentHUD()
    
    # 启动后台逻辑线程
    logic_thread = threading.Thread(target=run_agent_logic, args=(hud,), daemon=True)
    logic_thread.start()
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
