import subprocess
import time
import base64
import requests
import json
import os
import xml.etree.ElementTree as ET

# Configuration (Matching humanoid_agent.py)
MODEL_URL = "http://localhost:11434/v1/chat/completions"
MODEL_NAME = "gemma4:latest"

def run_adb(cmd):
    start = time.time()
    res = subprocess.run(["adb"] + cmd, capture_output=True, text=True)
    return res, time.time() - start

def profile_interaction():
    stats = {}
    print(f"[*] Starting High-Precision Profiling on {MODEL_NAME}...\n")

    # 1. ADB Dump & Pull XML
    print("[1/5] Profiling ADB UI Dump...")
    _, t_dump = run_adb(["shell", "uiautomator", "dump", "/sdcard/profile.xml"])
    _, t_pull_xml = run_adb(["pull", "/sdcard/profile.xml", "profile.xml"])
    stats['adb_xml_total'] = t_dump + t_pull_xml
    stats['adb_xml_dump'] = t_dump
    stats['adb_xml_pull'] = t_pull_xml

    # 2. ADB Screencap & Pull
    print("[2/5] Profiling ADB Screencap...")
    _, t_cap = run_adb(["shell", "screencap", "-p", "/sdcard/profile.png"])
    _, t_pull_img = run_adb(["pull", "/sdcard/profile.png", "profile.png"])
    stats['adb_img_total'] = t_cap + t_pull_img
    stats['adb_img_cap'] = t_cap
    stats['adb_img_pull'] = t_pull_img

    # 3. Local Processing (Inventory Extraction)
    print("[3/5] Profiling Inventory Extraction...")
    start_proc = time.time()
    # Mocking the cleaning logic
    try:
        tree = ET.parse("profile.xml")
        root = tree.getroot()
        elements = []
        for node in root.iter('node'):
            text = node.get('text', '')
            if text: elements.append(text)
        inventory_str = "\n".join(elements[:50]) # Sample
    except:
        inventory_str = "Error"
    stats['local_processing'] = time.time() - start_proc

    # 4. Image Encoding
    start_enc = time.time()
    with open("profile.png", "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
    stats['img_b64_encoding'] = time.time() - start_enc

    # 5. LLM Inference (Prefill vs Generation)
    print("[4/5] Profiling LLM Inference (Network + Inference)...")
    prompt = f"Target: Click Search. UI Inventory: {inventory_str}"
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
        ]}],
        "temperature": 0,
        "stream": False # We want total time
    }
    
    start_llm = time.time()
    response = requests.post(MODEL_URL, json=payload)
    stats['llm_total_latency'] = time.time() - start_llm
    
    # Try to get token counts if Ollama provides them
    res_json = response.json()
    # Note: /v1/chat/completions might not have usage in some Ollama versions, 
    # but let's check.
    usage = res_json.get('usage', {})
    stats['prompt_tokens'] = usage.get('prompt_tokens', 0)
    stats['completion_tokens'] = usage.get('completion_tokens', 0)

    # 6. Summary
    print("\n" + "="*40)
    print("PROFILING RESULTS (Seconds)")
    print("="*40)
    print(f"ADB XML (Dump+Pull):   {stats['adb_xml_total']:.2f}s  (Dump: {stats['adb_xml_dump']:.2f}s, Pull: {stats['adb_xml_pull']:.2f}s)")
    print(f"ADB IMG (Cap+Pull):   {stats['adb_img_total']:.2f}s  (Cap: {stats['adb_img_cap']:.2f}s, Pull: {stats['adb_img_pull']:.2f}s)")
    print(f"Local Processing:     {stats['local_processing']:.2f}s")
    print(f"Base64 Encoding:      {stats['img_b64_encoding']:.2f}s")
    print(f"LLM Inference Total:  {stats['llm_total_latency']:.2f}s")
    print("-" * 40)
    
    total = stats['adb_xml_total'] + stats['adb_img_total'] + stats['local_processing'] + stats['img_b64_encoding'] + stats['llm_total_latency']
    print(f"TOTAL CYCLE TIME:     {total:.2f}s")
    
    if stats['prompt_tokens'] > 0:
        print(f"Tokens:               {stats['prompt_tokens']} (In) / {stats['completion_tokens']} (Out)")
    print("="*40)

if __name__ == "__main__":
    profile_interaction()
