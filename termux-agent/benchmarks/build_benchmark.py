import os
import re
import json

def extract_from_logs():
    data = []
    log_dirs = sorted([d for d in os.listdir("logs") if d.startswith("run_")])
    
    for run_dir in log_dirs:
        log_path = os.path.join("logs", run_dir, "agent_debug.log")
        if not os.path.exists(log_path): continue
            
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Match the header precisely
        # ==================== STEP 1 [DECISION] ====================
        pattern = r"={10,}\s+STEP\s+\d+\s+\[DECISION\]\s+={10,}"
        blocks = re.split(pattern, content)
        print(f"File {log_path}: found {len(blocks)-1} decision blocks.")
        
        for i, block in enumerate(blocks[1:]):
            if "[PROMPT]:" not in block or "[RESPONSE]:" not in block:
                continue
            
            prompt_parts = block.split("[PROMPT]:")
            after_prompt = prompt_parts[1].split("[RESPONSE]:")
            prompt = after_prompt[0].strip()
            response = after_prompt[1].strip()
            response = re.split(r"={10,}\s+STEP", response)[0].strip()
            
            step_num_match = re.search(r"STEP\s+(\d+)", blocks[i]) # This won't work because blocks are split
            # Actually, the step number is in the part we split ON.
            # Let's use re.finditer to get both header and content.
            
    # Redoing with finditer for better control
    data = []
    for run_dir in log_dirs:
        log_path = os.path.join("logs", run_dir, "agent_debug.log")
        if not os.path.exists(log_path): continue
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Find all Decision headers and their content until next header
        pattern = r"(={10,}\s+STEP\s+(\d+)\s+\[DECISION\].*?)(?=^={10,}\s+STEP|\Z)"
        matches = re.finditer(pattern, content, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            full_block = match.group(1)
            step_num = match.group(2)
            
            if "[PROMPT]:" in full_block and "[RESPONSE]:" in full_block:
                prompt = full_block.split("[PROMPT]:")[1].split("[RESPONSE]:")[0].strip()
                response = full_block.split("[RESPONSE]:")[1].strip()
                
                img_path = os.path.join("logs", run_dir, f"step_{step_num}_before.png")
                if not os.path.exists(img_path):
                    # Try step_{step_num}.png (some logs might use this)
                    img_path = os.path.join("logs", run_dir, f"step_{step_num}.png")
                
                if os.path.exists(img_path):
                    data.append({
                        "source": f"{run_dir}_step_{step_num}",
                        "prompt": prompt,
                        "img": img_path,
                        "expected": response
                    })
    return data

def generate_zhihu_scenarios():
    zhihu_scenarios = []
    for i in range(1, 6):
        img = f"step_{i}.png"
        list_file = f"step_{i}_list.txt"
        if not os.path.exists(img) or not os.path.exists(list_file): continue
        with open(list_file, "r") as f:
            elements = f.readlines()
        for line in elements:
            match = re.search(r"ID (\d+): '(.*?)'", line)
            if match:
                node_id = int(match.group(1))
                label = match.group(2)
                if len(label) < 3 or any(x in label for x in ["首页", "直答", "消息", "未登录", "关注", "推荐", "热榜"]):
                    continue
                zhihu_scenarios.append({
                    "source": f"zhihu_step_{i}_{node_id}",
                    "img": img,
                    "goal": f"点击知乎上的这个内容：'{label}'",
                    "expected_id": node_id,
                    "list": "".join(elements)
                })
                if len(zhihu_scenarios) >= 100: break
    return zhihu_scenarios

if __name__ == "__main__":
    log_data = extract_from_logs()
    print(f"Extracted {len(log_data)} from logs.")
    zhihu_data = generate_zhihu_scenarios()
    print(f"Generated {len(zhihu_data)} from Zhihu.")
    combined = log_data + zhihu_data
    final_data = combined[:100]
    with open("benchmark_100.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_data)} scenarios to benchmark_100.json")
