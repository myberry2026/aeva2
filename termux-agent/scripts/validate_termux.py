#!/usr/bin/env python3
import sys
import os
import requests
import json
from pathlib import Path

def print_result(name, success, detail=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"[{status}] {name}: {detail}")
    return success

def validate():
    print("=== Termux Deployment Validation ===\n")
    all_pass = True

    # 1. 检查 Python 依赖
    try:
        import requests
        import PIL
        import websockets
        print_result("Python Dependencies", True, "requests, Pillow, websockets are installed")
    except ImportError as e:
        all_pass &= print_result("Python Dependencies", False, f"Missing: {e}")

    # 2. 检查 Bridge 连通性 (Localhost)
    # 注意: 假设 bridge 在 8765 端口
    bridge_url = "http://localhost:8765/ping"
    try:
        # 获取 token (尝试从 prefs 读取)
        token = ""
        # 这种路径在 Termux 内部可能访问不到，取决于权限，我们尝试直接 ping 
        r = requests.get(bridge_url, timeout=5)
        data = r.json()
        ax_running = data.get("accessibilityService", False)
        all_pass &= print_result("Bridge", True, f"Ping OK. AX Service: {ax_running}")
        if not ax_running:
            print("   (Hint: Enable 'Bridge' in Accessibility settings)")
    except Exception as e:
        all_pass &= print_result("Bridge", False, f"Cannot reach bridge at {bridge_url}. Error: {e}")

    # 3. 检查 LLM Server 连通性
    # 优先检查本地 8080 (On-device), 其次检查远程 1234 (Win)
    local_llm_url = "http://localhost:8080/v1/models"
    remote_llm_url = "http://100.113.214.52:1234/v1/models"
    
    llm_found = False
    try:
        r = requests.get(local_llm_url, timeout=5)
        if r.status_code == 200:
            models = r.json().get('data', [])
            all_pass &= print_result("On-Device LLM", True, f"Server alive at 8080. Models: {len(models)}")
            llm_found = True
    except:
        pass

    if not llm_found:
        try:
            r = requests.get(remote_llm_url, timeout=5)
            if r.status_code == 200:
                models = r.json().get('data', [])
                all_pass &= print_result("Remote LLM", True, f"Server alive at 1234. Models: {len(models)}")
                llm_found = True
        except Exception as e:
            all_pass &= print_result("LLM Server", False, f"Cannot reach any LLM server. Error: {e}")
    
    all_pass &= llm_found

    # 4. 检查项目代码完整性
    root = Path(__file__).resolve().parents[1]
    required_files = ["humanoid_agent.py", "bridge_client.py", "scripts/deploy_local.sh"]
    missing = [f for f in required_files if not (root / f).exists()]
    if not missing:
        all_pass &= print_result("Project Files", True, f"Found {len(required_files)} core files")
    else:
        all_pass &= print_result("Project Files", False, f"Missing: {', '.join(missing)}")

    print("\n" + ("=" * 40))
    if all_pass:
        print("🎉 TERMUX DEPLOYMENT IS READY!")
        sys.exit(0)
    else:
        print("⚠️ SOME COMPONENTS ARE MISSING OR UNREACHABLE.")
        sys.exit(1)

if __name__ == "__main__":
    validate()
