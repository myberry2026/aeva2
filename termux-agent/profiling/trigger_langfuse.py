import os
import sys

# Injecting the keys provided by the user
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-afa343c3-b7e1-4dc1-bac9-ff3a1daa9159"
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-6228d3f8-4b84-486c-b0ad-a8292b25b307"
os.environ["LANGFUSE_HOST"] = "https://us.cloud.langfuse.com"

import time
import requests
import base64
import json
from langfuse_helper import safe_observe, update_trace
from langfuse import Langfuse

MODEL_URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL_NAME = "google/gemma-4-e4b"

@safe_observe(name="Full_Agent_Step")
def main_cycle():
    print("[*] Starting Langfuse Monitored Cycle...")
    
    # 1. Simulate ADB Interaction
    adb_prep()
    
    # 2. Call the remote LLM
    call_llm()
    
    print("[*] Cycle complete. Syncing to Langfuse...")

@safe_observe(name="System_ADB_Prep")
def adb_prep():
    print("  -> Performing ADB Dump and Screencap...")
    # Simulating the optimized concurrent ADB time we measured earlier
    time.sleep(2.0) 
    return True

@safe_observe(name="LLM_Inference_Remote")
def call_llm():
    print(f"  -> Sending prompt and image to {MODEL_NAME}...")
    
    # We use the existing test.png from earlier runs
    img_path = "../test.png"
    if not os.path.exists(img_path):
        img_path = "test.png" # fallback
        
    try:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"Image not found, using dummy data. Error: {e}")
        img_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    # Using the optimized prompt (short thought)
    prompt = """
    Target: Click Search. 
    Inventory: 
    ID 0: 'Search' @ [500, 200]
    ID 1: 'Home' @ [100, 200]
    
    Return JSON format: {"thought": "Keep under 5 words.", "action": "click", "id": 0}
    """
    
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
        ]}],
        "temperature": 0
    }
    
    try:
        r = requests.post(MODEL_URL, json=payload, timeout=60)
        res_json = r.json()
        
        usage = res_json.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        prefill_ms = usage.get("prompt_eval_duration", 0)
        
        update_trace(
            metadata={
                "model": MODEL_NAME, 
                "prefill_ms": prefill_ms,
                "optimized_prompt": True
            },
            tags=["demo", "remote_gemma"],
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens
        )
        print("  -> LLM response received successfully.")
    except Exception as e:
        print(f"  -> Error calling LLM: {e}")

if __name__ == "__main__":
    # Ensure working directory is correct for imports
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    main_cycle()
    
    # Flush Langfuse telemetry before exiting
    langfuse = Langfuse()
    langfuse.flush()
    print("[*] Trace successfully pushed to your Langfuse dashboard!")
