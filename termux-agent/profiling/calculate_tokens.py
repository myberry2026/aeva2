import tiktoken
import sys

def calculate_tokens(text):
    # 使用 cl100k_base 编码器 (GPT-4 的标准，虽然与 Gemma 有微小差异，但数量级基本一致)
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    return len(tokens)

def explain_vision_tokens(width, height):
    """
    大多数 VLM (如 Gemma-Vision, GPT-4V) 处理图片的逻辑：
    1. 缩放图片，使其适应模型的最大分辨率 (例如 1024x1024 或 896x896)。
    2. 将图片切分成固定大小的 Patch (通常是 14x14 或 28x28 像素)。
    3. 每个 Patch 被编码为一个 Visual Token。
    """
    # 以 OpenAI 的高分辨率计费标准为例 (Gemma/LlaVA 原理类似)：
    # 假设 Patch 尺寸为 28x28
    patch_size = 28
    # 缩小到最大短边不超 768，长边不超过 2000
    scaled_w, scaled_h = width, height
    if width > 1080 or height > 1080:
        scale = 1080 / max(width, height)
        scaled_w, scaled_h = int(width * scale), int(height * scale)
        
    tiles_w = (scaled_w + patch_size - 1) // patch_size
    tiles_h = (scaled_h + patch_size - 1) // patch_size
    
    total_patches = tiles_w * tiles_h
    # 通常 VLM 会把每一个 patch 映射为一个 token，加上一些 base token
    estimated_vision_tokens = total_patches + 85 
    
    return {
        "original": f"{width}x{height}",
        "scaled": f"{scaled_w}x{scaled_h}",
        "tiles": f"{tiles_w} x {tiles_h}",
        "estimated_tokens": estimated_vision_tokens
    }

if __name__ == "__main__":
    # 1. 模拟我们发送的文本 (Prompt + Inventory)
    sample_text = """
    你是一个 Android 自动化专家，正在驱动一台真实手机。
    当前屏幕真实分辨率: 1080 x 2400 (所有坐标点 [x, y] 必须在此范围内)

    【总目标】: 打开浏览器搜索 'weather in San Francisco'
    【任务清单】（[x]=已完成 [→]=当前焦点 [ ]=待办）:
    [→] 1. 当前在Android系统桌面

    【当前可交互清单】:
    ID 0: 'Web View' @ [540, 1232]
    ID 1: 'Home' @ [63, 201]
    ID 2: 'location_bar_status' @ [179, 201]
    ID 3: 'Connection is secure' @ [178, 201]
    ID 4: 'google.com/search?q=cute+cat+wallpaper' @ [446, 201]
    ID 5: 'toolbar_buttons' @ [886, 201]
    ID 6: 'New tab' @ [760, 201]
    """
    
    # 将文本重复几次以模拟真实的 50+ 个 UI 元素列表
    full_text = sample_text + ("ID X: 'Sample Button' @ [500, 500]\n" * 40)
    
    text_token_count = calculate_tokens(full_text)
    
    # 2. 模拟手机截图分辨率
    vision_stats = explain_vision_tokens(1080, 2400)
    
    print("=== TOKEN CALCULATION BREAKDOWN ===")
    print(f"[1] 文本 Token (Text Prompts):")
    print(f"    - 字符数: {len(full_text)}")
    print(f"    - 估算 Token: ~{text_token_count} tokens")
    print(f"    - 计算规则: 英文大约 1 token ≈ 4 个字母 (0.75词)。中文较耗 token，通常 1 个汉字 ≈ 1 到 2 个 token。")
    
    print(f"\n[2] 视觉 Token (Image Encoding):")
    print(f"    - 原始分辨率: {vision_stats['original']}")
    print(f"    - 切片网格: {vision_stats['tiles']} (基于 28x28 patch)")
    print(f"    - 估算 Token: ~{vision_stats['estimated_tokens']} tokens")
    print(f"    - 计算规则: 大模型不看完整的 1.5MB 像素，而是把图片切成一个个小方块(Patch)。一个方块就是一个 Token。")
    
    print(f"\n[3] 每次请求的总成本 (Total Input):")
    print(f"    - ~{text_token_count + vision_stats['estimated_tokens']} Tokens")
    print("===================================")
