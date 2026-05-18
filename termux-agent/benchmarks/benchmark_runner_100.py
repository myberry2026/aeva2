import requests
import time
import base64
import json
import re

def call_gemma(prompt, img_path):
    url = "http://localhost:11434/v1/chat/completions"
    try:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
    except:
        return None, 0, None

    system_msg = {"role": "system", "content": "You are a specialized Android automation robot. Output ONLY raw JSON."}
    user_content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
    ]

    payload = {
        "model": "gemma4:latest",
        "messages": [system_msg, {"role": "user", "content": user_content}],
        "temperature": 0
    }

    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=60)
        duration = time.time() - start_time
        res_json = response.json()
        content = res_json['choices'][0]['message'].get("content", "")
        usage = res_json.get("usage")
        return content, duration, usage
    except Exception as e:
        return None, 0, None

def parse_json(text):
    if not text: return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)
    except:
        return None

def run_100_benchmark():
    import os
    json_path = os.path.join(os.path.dirname(__file__), "benchmark_100.json")
    with open(json_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    results = []
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    print(f"{'No':<3} | {'Source':<30} | {'Status':<6} | {'Time(s)':<8} | {'Tokens(I/O)':<12}")
    print("-" * 75)

    for i, s in enumerate(scenarios):
        # Construct prompt
        if "prompt" in s:
            prompt = s["prompt"]
        else:
            prompt = f"""
            Current Screen Context:
            Goal: {s['goal']}
            Interactive Elements:
            {s['list']}
            Analyze screenshot and identify the BEST element ID.
            Return ONLY JSON: {{"thought": "...", "action": "click", "id": ID}}
            """

        ans, duration, usage = call_gemma(prompt, s["img"])
        pred = parse_json(ans)
        
        # Track tokens
        usage_str = "N/A"
        if usage:
            p_tokens = usage.get("prompt_tokens", 0)
            c_tokens = usage.get("completion_tokens", 0)
            total_prompt_tokens += p_tokens
            total_completion_tokens += c_tokens
            usage_str = f"{p_tokens}/{c_tokens}"

        # Validation Logic
        status = "FAIL"
        if pred:
            if "expected_id" in s:
                if pred.get("id") == s["expected_id"]:
                    status = "PASS"
            else:
                # Log-based: compare action and target (id or pkg)
                try:
                    expected = parse_json(s["expected"])
                    if expected and pred.get("action") == expected.get("action"):
                        if expected.get("id") is not None:
                            if pred.get("id") == expected.get("id"): status = "PASS"
                        elif expected.get("pkg"):
                            if pred.get("pkg") == expected.get("pkg"): status = "PASS"
                        elif expected.get("point"):
                            # Check if point is close (within 50px)
                            p1, p2 = pred.get("point"), expected.get("point")
                            if p1 and p2 and abs(p1[0]-p2[0]) < 50 and abs(p1[1]-p2[1]) < 50:
                                status = "PASS"
                        else:
                            status = "PASS" # Same action, no specific target
                except:
                    pass

        print(f"{i+1:<3} | {s['source'][:30]:<30} | {status:<6} | {duration:.2f}     | {usage_str:<12}")
        results.append({"id": i+1, "status": status, "time": duration})

    # Summary
    passes = sum(1 for r in results if r['status'] == "PASS")
    avg_time = sum(r['time'] for r in results) / len(results) if results else 0
    total_tokens = total_prompt_tokens + total_completion_tokens
    print("-" * 75)
    print(f"Final Score: {passes}/100 | Avg Time: {avg_time:.2f}s")
    print(f"Total Tokens: {total_tokens} (Prompt: {total_prompt_tokens}, Completion: {total_completion_tokens})")

if __name__ == "__main__":
    run_100_benchmark()
