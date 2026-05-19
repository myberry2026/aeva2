import sys
import os

# 将 bridge-android 根目录加入路径，以便导入 tools.android_relay
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.android_relay import start_relay
import time
import logging

logging.basicConfig(level=logging.INFO)

PAIRING_CODE = "Q5M68Y"
PORT = 8766

print(f"Starting local relay with code {PAIRING_CODE} on port {PORT}...")
start_relay(PAIRING_CODE, PORT)

# Keep the main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping relay...")
