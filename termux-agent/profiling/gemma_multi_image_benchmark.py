import requests
import base64
import json
import os
import time
import asyncio
import aiohttp
from datetime import datetime

# --- 配置 ---
URL = "http://100.113.214.52:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"
TEST_PROMPT = "Describe the UI elements you see in these images and determine if there is any inconsistency between them."

# 尝试寻找本地图片
SCREENSHOT_DIR = "screenshots"
if not os.path.exists(SCREENSHOT_DIR):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def get_test_images(count):
    """获取指定数量的测试图片路径"""
    images = []
    # 优先从 screenshots 目录取
    if os.path.exists(SCREENSHOT_DIR):
        files = [os.path.join(SCREENSHOT_DIR, f) for f in os.listdir(SCREENSHOT_DIR) if f.endswith(('.png', '.jpg'))]
        images = files[:count]
    
    # 如果不够，从 logs 目录搜刮
    if len(images) < count:
        for root, dirs, files in os.walk("logs"):
            for f in files:
                if f.endswith(".png") and "before" in f:
                    images.append(os.path.join(root, f))
                    if len(images) >= count:
                        break
            if len(images) >= count: break
            
    return images

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

# --- 同步调用 (用于测试单请求多图延迟) ---
def call_gemma_multi_image(image_paths, prompt=TEST_PROMPT):
    user_content = []
    for path in image_paths:
        b64 = encode_image(path)
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })
    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "max_tokens": 512
    }

    start = time.time()
    try:
        print(f"[*] Sending request with {len(image_paths)} images...")
        resp = requests.post(URL, json=payload, timeout=120)
        duration = time.time() - start
        if resp.status_code == 200:
            res_json = resp.json()
            usage = res_json.get("usage", {})
            content = res_json['choices'][0]['message'].get('content', '')
            print(f"    [OK] Received response in {duration:.2f}s. Tokens: {usage.get('total_tokens')}")
            return {
                "success": True,
                "latency": duration,
                "usage": usage,
                "content_len": len(content)
            }
        else:
            print(f"    [Error] Status {resp.status_code}: {resp.text}")
            return {"success": False, "error": resp.status_code}
    except Exception as e:
        print(f"    [Exception] {e}")
        return {"success": False, "error": str(e)}

# --- 异步并发调用 (用于测试同时发 N 个请求) ---
async def async_call_gemma(session, image_paths, req_id):
    user_content = []
    for path in image_paths:
        b64 = encode_image(path)
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })
    user_content.append({"type": "text", "text": f"Request {req_id}: {TEST_PROMPT}"})

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "temperature": 0.2
    }

    start = time.time()
    try:
        async with session.post(URL, json=payload, timeout=120) as resp:
            duration = time.time() - start
            if resp.status == 200:
                res_json = await resp.json()
                usage = res_json.get("usage", {})
                total_tokens = usage.get("total_tokens", 0)
                print(f"    [Req {req_id}] Done in {duration:.2f}s, Tokens: {total_tokens}")
                return {"id": req_id, "latency": duration, "success": True, "tokens": total_tokens}
            else:
                text = await resp.text()
                return {"id": req_id, "success": False, "error": f"Status {resp.status}: {text[:100]}"}
    except Exception as e:
        return {"id": req_id, "success": False, "error": str(e)}

async def run_concurrent_test(n_requests, images_per_req):
    test_images = get_test_images(images_per_req)
    if not test_images:
        print("!!! No test images found.")
        return

    print(f"\n[Stress Test] Sending {n_requests} concurrent requests, each with {images_per_req} images...")
    start_total = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [async_call_gemma(session, test_images, i) for i in range(n_requests)]
        results = await asyncio.gather(*tasks)
    
    total_duration = time.time() - start_total
    success_results = [r for r in results if r['success']]
    
    print(f"\n--- Concurrent Test Results ({n_requests} requests) ---")
    print(f"Total Wall Time: {total_duration:.2f}s")
    
    if success_results:
        success_latencies = [r['latency'] for r in success_results]
        total_tokens = sum(r.get('tokens', 0) for r in success_results)
        
        avg_latency = sum(success_latencies)/len(success_latencies)
        tps = total_tokens / total_duration
        tpm = tps * 60
        
        print(f"Avg Latency: {avg_latency:.2f}s")
        print(f"Throughput (Total Tokens/s): {tps:.2f}")
        print(f"Throughput (Total Tokens/m): {tpm:.0f}")
        print(f"Min/Max Latency: {min(success_latencies):.2f}s / {max(success_latencies):.2f}s")
    else:
        print("!!! No requests succeeded in this concurrent test.")
        for r in results:
            if not r['success']:
                print(f"    [Error ID {r['id']}] {r.get('error')}")
    
    print(f"Success Rate: {len(success_results)}/{n_requests}")

# --- 主运行逻辑 ---
def main():
    print(f"=== Gemma 4 Remote Vision Benchmark ===")
    print(f"Target URL: {URL}")
    print(f"Model: {MODEL}\n")

    # 1. 测试单请求多图模式 (One request, many images)
    scenarios = [1, 3, 10]
    perf_results = []

    for count in scenarios:
        imgs = get_test_images(count)
        if len(imgs) < count:
            print(f"Warning: Only found {len(imgs)} images for scenario {count}")
        
        print(f"\n--- Scenario: Single Request with {len(imgs)} images ---")
        res = call_gemma_multi_image(imgs)
        res['count'] = len(imgs)
        perf_results.append(res)

    # 打印对比表
    print("\n" + "="*95)
    print(f"{'Images':<8} | {'Status':<6} | {'Lat (s)':<8} | {'In TPS':<10} | {'Out TPS':<10} | {'Total TPS':<10} | {'TPM (min)':<10}")
    print("-" * 95)
    for r in perf_results:
        if r['success']:
            u = r['usage']
            lt = r['latency']
            in_tps = u.get('prompt_tokens', 0) / lt
            out_tps = u.get('completion_tokens', 0) / lt
            total_tps = u.get('total_tokens', 0) / lt
            tpm = total_tps * 60
            print(f"{r['count']:<8} | {'OK':<6} | {lt:>8.2f} | {in_tps:>10.1f} | {out_tps:>10.1f} | {total_tps:>10.1f} | {tpm:>10.0f}")
        else:
            print(f"{r['count']:<8} | {'FAIL':<6} | {'N/A':>8} | {'N/A':>10} | {'N/A':>10} | {'N/A':>10} | {'N/A':>10}")
    print("="*95)

    # 2. 并发压力测试 (Multiple requests at once)
    # 同时发 3 个请求
    asyncio.run(run_concurrent_test(3, 1))
    
    # 同时发 10 个请求
    asyncio.run(run_concurrent_test(10, 1))

if __name__ == "__main__":
    main()
