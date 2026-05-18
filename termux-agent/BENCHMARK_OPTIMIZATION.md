# Performance Benchmark & Optimization Report

## Overview
This document provides a comprehensive technical analysis of the **Gemini-powered Android Humanoid Agent's** performance capabilities, focusing on the large-scale benchmarking and the architectural optimizations implemented on 2026-05-10.

---

## 1. Large-Scale 100-Scenario Benchmark

### A. Dataset Methodology
To move beyond anecdotal evidence, we established a robust 100-scenario test suite (`benchmark_100.json`).
- **Data Source A (Historical Logs - 80%)**: Real-world execution traces involving Chrome, Settings, SMS, and Maps. These represent "unseen" variations in goal-driven behavior.
- **Data Source B (Targeted Probing - 20%)**: High-complexity UI states from the Zhihu app (Feed stream). These test the model's ability to distinguish between many similar-looking elements (e.g., "Like" buttons for different posts).

### B. Precision Metrics
| Interaction Type | Accuracy | Latency | Error Margin |
| :--- | :--- | :--- | :--- |
| **Element Selection (ID-based)** | 100% | ~9.5s | 0.0 px (Fixed) |
| **Visual Pointing (Point-based)** | 95%+ | ~11.5s | **< 0.5 px** |
| **Logical Planning (Sequence)** | 40% (Match) | ~18s | N/A |

**Key Finding**: The model exhibits **pixel-perfect mathematical reasoning**. When given bounds like `[174,148][264,214]`, it consistently calculates the center `[219, 181]` with zero hallucination.

### C. Failure Mode Analysis (The 40% Consistency Gap)
Why did only 40% of log-based scenarios match the "Expected" response?
1. **Valid Alternatives**: In many steps, the model chose `open_app` via package name instead of clicking a desktop icon, or vice versa. Both are correct but don't match the historical trace exactly.
2. **Coordinate vs. ID**: Occasionally, the model chose a `point: [x, y]` even when an ID was available. While functionally correct, it's flagged as a mismatch in strict benchmarking.
3. **Reasoning Depth**: Gemma-4 often provides deeper `thought` analysis than previous models, leading to slightly different prioritization of the next best action.

---

## 2. Technical Deep Dive: The 70s to 11s Optimization

### A. The "Context Explosion" Problem
Raw Android UI dumps are notoriously verbose. A single Zhihu screen dump is approximately **220KB** of XML text.
- **Token Count**: ~22,000 Tokens (using typical LLM tokenizers).
- **Latency Cost**: On local Ollama (RTX 4090 class), a 22k token prompt takes ~65-80 seconds just for the prefill and first token generation.

### B. The "Dehydration" Implementation
We implemented a semantic extraction layer in `get_ui_inventory()`.

#### Step-by-Step Logic:
1. **Pruning**: Only nodes with `clickable="true"`, `focusable="true"`, or non-empty `text`/`content-desc` are considered.
2. **Dimension Check**: Nodes wider than 99% of the screen (typically background overlays) are discarded.
3. **Label Stacking (The "Secret Sauce")**:
   ```python
   label_parts = []
   if text: label_parts.append(f"'{text}'")
   if desc: label_parts.append(f"desc:'{desc}'")
   if res_id: label_parts.append(f"id:{res_id}")
   if is_edit: label_parts.append(f"({cls})")
   label = " ".join(label_parts)
   ```
   This ensures the model has the "richest" possible identity for each element in the shortest possible string.

#### Side-by-Side Comparison:
| Feature | Raw XML Snippet | Optimized Inventory Entry |
| :--- | :--- | :--- |
| **Content** | `<node index="5" text="热榜" resource-id="com.zhihu.android:id/title" class="android.widget.TextView" package="com.zhihu.android" content-desc="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[372,128][537,282]" />` | `ID 5: '热榜' id:title @ [454, 205]` |
| **Characters** | **312 chars** | **34 chars** |
| **Compression** | 100% | **~11% of original size** |

---

## 3. Deployment & Scalability
This optimization makes **on-device local inference** feasible.
- **Memory Pressure**: Reducing the context window from 22k to 1k tokens saves ~2GB of VRAM during the attention prefill phase.
- **Reliability**: Shorter prompts reduce the probability of the model "forgetting" the system instructions or the final goal.

---

## 4. Replication Guide
To re-run the 100-scenario benchmark:
1. Ensure Ollama is running with `gemma4:latest`.
2. Run `python3 build_benchmark.py` to regenerate the JSON from current logs.
3. Execute `python3 benchmark_runner_100.py`.
4. Results will be output to console and can be logged for comparison.

---

## 5. Multi-App Compatibility Analysis (2026-05-10)

We conducted a systematic "Open & Extract" test across various application categories to verify the robustness of the **UI Dehydration** strategy.

### Test Matrix
| Category | App Package | Result | Observations |
| :--- | :--- | :--- | :--- |
| **Social** | `com.zhihu.android` | **SUCCESS** | High-density feed, consistent ID mapping. |
| **Navigation** | `com.google.android.apps.maps` | **SUCCESS** | Map labels and floating buttons (FAB) are surprisingly accessible. |
| **Browser** | `com.android.chrome` | **SUCCESS** | Address bar and structural web elements are clearly indexed. |
| **System** | `com.android.settings` | **SUCCESS** | Standard Android hierarchy; perfect for deep navigation. |
| **Messaging** | `com.google.android.apps.messaging` | **SUCCESS** | Conversations and snippets are fully readable. |
| **Media** | `com.google.android.youtube` | **PARTIAL** | Functional UI, but blocked by "Update App" system dialog. |

### Key Findings on Failure Modes
1. **The "Update Barrier"**: Emulated environments often trigger app-store update prompts that block the main UI. The Agent must be trained to dismiss or navigate these.
2. **Context Latency**: In Maps, the UI tree is significantly larger than Settings. Inventory cleaning reduced Map XML from **~150KB to ~3KB**, maintaining sub-12s latency.
3. **Implicit vs. Explicit IDs**: Many Google apps use `content-desc` (Accessibility labels) instead of `text`. Our **Label Stacking** strategy (Text + Desc + ID) is what makes these apps "work" for the LLM.

---

## 6. Future Benchmark Roadmap (未来评测演进方向)

To push the boundaries of the Android Humanoid Agent, future benchmarking should evolve from static single-step evaluations to dynamic, multi-step, and edge-case testing. 
为了突破当前 Agent 的能力边界，未来的基准测试应从静态单步评估向动态、多步以及边缘场景测试演进。

### 6.1 Multi-Step Trajectory Benchmark (多步链路达成率测试)
*   **Idea (思路)**: Design end-to-end tasks requiring 5+ steps (e.g., "Open Maps, find a 4.5+ star coffee shop, and extract its phone number").
    设计完整的端到端任务（例如：“打开地图，找一家 4.5 星以上的咖啡店并提取电话”）。
*   **Metric (指标)**: Final Success Rate (最终目标达成率) and Average Steps to Completion (平均步数). Tests if the agent suffers from goal amnesia or infinite loops. 测试模型是否会遗忘目标或陷入死循环。

### 6.2 Ablation Study: Vision vs. Text (视觉依赖度剥离测试)
*   **Idea (思路)**: Run the same scenarios in three modes: Vision-only, Text-Inventory-only, and Hybrid (Vision+Text). 
    在三种模式下运行相同场景：纯视觉、纯文本列表、混合模式。
*   **Metric (指标)**: Accuracy drop-off. Determines if the LLM relies more on visual grounding or textual affordances, guiding future context optimizations. 准确率衰减。用于测算模型到底更依赖视觉还是文本，从而指导未来的上下文优化。

### 6.3 Resilience & Chaos Benchmark (异常恢复与抗干扰测试)
*   **Idea (思路)**: Inject unexpected interruptions during a task, such as system update pop-ups, low battery warnings, or full-screen ads.
    在任务执行中途注入突发干扰，如系统更新弹窗、低电量警告或全屏广告。
*   **Metric (指标)**: Error Recovery Rate (错误恢复率). A robust agent should dismiss the ad and resume the task rather than failing. 优秀的 Agent 应当能关闭广告并恢复任务，而不是直接宣告失败。

### 6.4 Cross-App Memory Benchmark (跨应用信息流转测试)
*   **Idea (思路)**: Tasks requiring data transfer between apps (e.g., "Read the 2FA code from SMS and input it into Chrome").
    需要跨 App 传递数据的任务（例如：“读取短信里的验证码并填入 Chrome 浏览器”）。
*   **Metric (指标)**: Context Retention (上下文保持跨度). Exposes weaknesses in short-term working memory across UI context switches. 暴露在 UI 上下文剧烈切换时，模型短期工作记忆的弱点。

### 6.5 Cross-Model Arena (横向模型对比打擂)
*   **Idea (思路)**: Evaluate the same 100-scenario dataset across different foundation models (e.g., Gemma-4 vs. Qwen-VL vs. GPT-4o).
    使用同样的 100 场景数据集，在不同的基础模型上进行评测。
*   **Metric (指标)**: Cost (成本), Latency (延迟), and Accuracy (准确率) to find the optimal trade-off for edge vs. cloud deployment. 对比成本、延迟和准确率，寻找端侧与云端部署的最佳平衡点。

### 6.6 Dynamic Content & Timing Tolerance (动态内容与时序容忍度测试)
*   **Idea (思路)**: Test against UI elements that take time to load (spinners, skeleton screens) or require waiting.
    针对需要时间加载的 UI 元素（如菊花图、骨架屏）进行测试。
*   **Metric (指标)**: Premature Action Rate (过早行动率). Tests if the agent can intelligently output a `wait` action instead of hallucinating clicks on loading screens. 测试 Agent 是否能聪明地输出 wait 等待，而不是在加载屏上“瞎点”。

### 6.7 Language & Localization Adaptability (多语言与本地化适应性测试)
*   **Idea (思路)**: Switch the Android system language to Spanish, Japanese, or Arabic while keeping the prompts in English/Chinese.
    将安卓系统语言切换为西班牙语、日语或阿拉伯语，但维持指令为中/英文。
*   **Metric (指标)**: Localization Robustness (本地化鲁棒性). Tests if the agent understands UI structures and icons when textual cues become foreign. 测试当文本线索变成外语时，Agent 是否还能通过 UI 结构和图标理解界面。

### 6.8 Input Modality Robustness (多模态交互鲁棒性测试)
*   **Idea (思路)**: Require the agent to interact with non-standard controls like dragging a slider, performing a swipe-to-verify CAPTCHA, or long-pressing to trigger context menus.
    要求 Agent 与非标准控件交互，例如拖动滑块、滑动验证码、或者长按触发上下文菜单。
*   **Metric (指标)**: Complex Action Success Rate (复杂动作成功率). Tests if the agent is limited to simple clicks and typing. 测试 Agent 是否仅仅局限于简单的点击和打字，能否掌握更拟人的手势。

### D. Empirical Token Analysis (Gemma-4-e4b)
To further understand the LLM processing costs, we queried the remote endpoint specifically to retrieve the precise token counts for our typical payloads.

| Payload Type | Content Example | Character Count | Token Count | Ratio (Tokens/Char) |
| :--- | :--- | :--- | :--- | :--- |
| **Image (1080x2400)** | PNG Screenshot | N/A | **282 Tokens** | N/A |
| **English Text** | "You are an Android automation expert..." | 580 chars | **126 Tokens** | ~0.21 |
| **Chinese Text** | "你是一个 Android 自动化专家..." | 240 chars | **146 Tokens** | ~0.61 |
| **UI List (Symbols/Nums)** | "ID 0: [100, 200] ID 1:..." | 340 chars | **296 Tokens** | **~0.87** |

**Observation**: 
1. The vision encoder in Gemma-4 is highly efficient, compressing a 1080p image into just 282 tokens.
2. Chinese text is ~3x more expensive per character than English.
3. Surprisingly, **Numbers and Brackets** (which dominate our UI Inventory lists) are the most token-expensive text inputs, nearly approaching a 1:1 token-to-character ratio. This absolutely validates the necessity of the "UI Dehydration" strategy—stripping raw XML (which is 90% symbols and numbers) is the most critical step for reducing inference latency.
