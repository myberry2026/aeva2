import subprocess
import os
import sys
import time
import requests
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from profiling.langfuse_helper import safe_observe, update_trace, flush_langfuse

load_dotenv()

def check_adb():
    print("[1/4] Checking ADB Connection...")
    res = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = [l for l in res.stdout.splitlines() if l.strip() and not l.startswith("List")]
    if not lines:
        print("❌ Error: No ADB devices found. Is your phone connected?")
        return False
    print(f"✅ Found {len(lines)} device(s): {lines[0]}")
    
    res = subprocess.run(["adb", "shell", "wm", "size"], capture_output=True, text=True)
    print(f"✅ Screen size: {res.stdout.strip()}")
    return True

def check_adb_keyboard():
    print("[2/4] Checking ADBKeyBoard...")
    res = subprocess.run(["adb", "shell", "ime", "list", "-s"], capture_output=True, text=True)
    if "com.android.adbkeyboard" in res.stdout:
        print("✅ ADBKeyBoard is installed and set as default IME.")
    else:
        print("⚠️ Warning: ADBKeyBoard not found or not default. Unicode typing may fail.")
        print("   Try: python agents/humanoid_agent.py (it will auto-install it)")
    return True

def check_langfuse():
    print("[3/4] Checking Langfuse Connectivity...")
    host = os.getenv("LANGFUSE_HOST")
    pk = os.getenv("LANGFUSE_PUBLIC_KEY")
    if not host or not pk:
        print("❌ Error: LANGFUSE_HOST or PUBLIC_KEY missing in .env")
        return False
    
    try:
        res = requests.get(f"{host}/api/public/health", timeout=5)
        if res.status_code == 200:
            print(f"✅ Langfuse host {host} is reachable.")
        else:
            print(f"⚠️ Langfuse host returned status {res.status_code}")
    except Exception as e:
        print(f"❌ Error: Could not reach Langfuse host: {e}")
        return False
    
    # Try a real trace
    @safe_observe(name="Health_Check_Trace")
    def ping_trace():
        update_trace(metadata={"type": "health_check"})
        return "ok"
    
    ping_trace()
    flush_langfuse()
    print("✅ Test trace sent to Langfuse.")
    return True

def check_llm():
    print("[4/4] Checking LLM Endpoint...")
    # Based on CURRENT_MODEL in humanoid_agent.py
    # Default is GEMMA at http://100.113.214.52:1234/v1
    url = "http://100.113.214.52:1234/v1/models"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            models = res.json().get("data", [])
            model_names = [m.get("id") for m in models]
            print(f"✅ LLM Endpoint reachable. Available models: {model_names}")
            if "google/gemma-4-e4b" in model_names:
                print("✅ Found target model: google/gemma-4-e4b")
            else:
                print(f"⚠️ Warning: Target model not found. Available: {model_names}")
        else:
            print(f"❌ Error: LLM Endpoint returned {res.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: Could not reach LLM Endpoint: {e}")
        return False
    return True

def main():
    print("=== Phone Vision System Health Check ===")
    print(f"Time: {time.ctime()}")
    print("-" * 40)
    
    results = [
        check_adb(),
        check_adb_keyboard(),
        check_langfuse(),
        check_llm()
    ]
    
    print("-" * 40)
    if all(results):
        print("🚀 ALL SYSTEMS GO! Your hackathon demo is ready.")
    else:
        print("⚠️ Some systems failed. Please check the logs above.")

if __name__ == "__main__":
    main()
