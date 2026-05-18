import concurrent.futures
import subprocess
import time

def run_adb(cmd):
    start = time.time()
    res = subprocess.run(["adb"] + cmd, capture_output=True, text=True)
    return time.time() - start

def _do_dump():
    return run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    
def _do_cap():
    return run_adb(["shell", "screencap", "-p", "/sdcard/view.png"])

if __name__ == "__main__":
    print("Testing Sequential...")
    t1 = _do_dump()
    t2 = _do_cap()
    print(f"Sequential Total: {t1 + t2:.2f}s (Dump: {t1:.2f}s, Cap: {t2:.2f}s)")
    
    print("\nTesting Concurrent...")
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_cap = executor.submit(_do_cap)
        f_dump = executor.submit(_do_dump)
        f_cap.result()
        f_dump.result()
    print(f"Concurrent Total: {time.time() - start_time:.2f}s")
