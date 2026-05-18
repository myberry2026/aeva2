import subprocess
import time
import base64
import requests
import json
import xml.etree.ElementTree as ET

MODEL_URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL_NAME = "google/gemma-4-e4b"

def run_adb(cmd):
    start = time.time()
    res = subprocess.run(["adb"] + cmd, capture_output=True, text=True)
    return res, time.time() - start

def _take_screenshot(path):
    return run_adb(["shell", "screencap", "-p", "/sdcard/view.png"])

def _do_dump():
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml_data, t = run_adb(["shell", "cat", "/sdcard/ui.xml"])
    return xml_data.stdout, t

def call_llm_stream(prompt, img_b64):
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
        ]}],
        "temperature": 0,
        "stream": True  # MUST use streaming to get TTFT
    }
    
    start_time = time.time()
    response = requests.post(MODEL_URL, json=payload, stream=True)
    
    ttft = 0
    first_token_received = False
    full_content = ""
    chunk_count = 0
    
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("data: "):
                data_str = decoded_line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data['choices'][0].get('delta', {})
                    if 'content' in delta:
                        if not first_token_received:
                            ttft = time.time() - start_time
                            first_token_received = True
                        full_content += delta['content']
                        chunk_count += 1
                except:
                    pass
                    
    total_time = time.time() - start_time
    gen_time = total_time - ttft
    
    return {
        "ttft": ttft,
        "gen_time": gen_time,
        "total_time": total_time,
        "content_length": len(full_content),
        "estimated_tokens": chunk_count, # roughly 1 token per chunk in stream
        "tps": chunk_count / gen_time if gen_time > 0 else 0
    }

def detailed_breakdown():
    print(f"=== DEEP LATENCY BREAKDOWN (Remote: {MODEL_NAME}) ===")
    
    # Prep
    _do_dump()
    _take_screenshot("test.png")
    with open("test.png", "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
    inventory = "ID 0: Search\nID 1: Home"
    
    print("\n[Scenario A] Baseline (Long Thought)")
    prompt_long = f"Target: Click Search. Inventory: {inventory}. Return JSON format: {{\"thought\": \"Please provide a very detailed and long step-by-step analysis of why you are choosing this action. Explain every single detail you see.\", \"action\": \"click\", \"id\": 0}}"
    res_long = call_llm_stream(prompt_long, img_b64)
    print(f"  - TTFT (Prefill Tax):       {res_long['ttft']:.2f}s")
    print(f"  - Generation Time:          {res_long['gen_time']:.2f}s")
    print(f"  - Total LLM Latency:        {res_long['total_time']:.2f}s")
    print(f"  - Output Size:              ~{res_long['estimated_tokens']} tokens ({res_long['tps']:.1f} tokens/sec)")

    print("\n[Scenario B] Optimized (Short Thought)")
    prompt_short = f"Target: Click Search. Inventory: {inventory}. Return JSON format: {{\"thought\": \"Keep under 5 words.\", \"action\": \"click\", \"id\": 0}}"
    res_short = call_llm_stream(prompt_short, img_b64)
    print(f"  - TTFT (Prefill Tax):       {res_short['ttft']:.2f}s")
    print(f"  - Generation Time:          {res_short['gen_time']:.2f}s")
    print(f"  - Total LLM Latency:        {res_short['total_time']:.2f}s")
    print(f"  - Output Size:              ~{res_short['estimated_tokens']} tokens ({res_short['tps']:.1f} tokens/sec)")
    
    print("\n=== CONCLUSION ===")
    print(f"By truncating the prompt, we save {res_long['gen_time'] - res_short['gen_time']:.2f}s of Generation Time.")
    print(f"The hard limit is the TTFT (Prefill), which is fixed at ~{res_short['ttft']:.2f}s.")

if __name__ == "__main__":
    detailed_breakdown()
