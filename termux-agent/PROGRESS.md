# Project Progress: Native Tool-Calling Architecture

## [2026-05-12] Milestone: V3.0 Ultimate Arena Passed
*   **Status**: ✅ Production Ready
*   **Result**: 61.7% success rate across 60 cases.
*   **Key Success**: 
    *   Unified 60-case benchmark (Single, 2-Turn, 3-Turn, 5-Turn).
    *   Solved "Summarizer Trap" with Reinforced Prompt.
    *   Enabled Parallel Tool Execution (e.g., Triple Tool Calling).
    *   First successful 5-turn marathon (Travel/System cleanup).

## [2026-05-12] V2.0: Multi-Turn Logical Hardening
*   **Status**: ✅ Completed
*   **Achievement**: 71.4% Multi-turn success rate in Pro mode.
*   **Learning**: Native tool_calls- 解决了 `teleport` 工具在处理非 JSON 参数时的解析偏差。

### Debugging
- 编写了 `scripts/test_context_limit.py` 压力测试脚本。
- 确认远程端点 (google/gemma-4-e4b) 的 context window 限制为 **4608 tokens**，解释了 Agent 在多轮对话或大 payload 下的失效。
parsing errors.

## [2026-05-12] V1.0: Native Tool-Calling Migration
*   **Status**: ✅ Completed
*   **Achievement**: Ported 22 tools to Native Schema.
*   **Baseline**: 60.0% Single-turn success.

## [2026-05-12] Milestone: Termux Compatibility Hardening
*   **Status**: ✅ Completed
*   **Achievement**: Removed heavy `transformers` dependency from `tool_layer.py`.
*   **Learning**: Minimal `get_json_schema` implementation reduces deployment footprint and fixes `ModuleNotFoundError` on Termux.

## Next Steps
1.  **Mainline Integration**: Merge `REINFORCED_PROMPT` and `tool_calls` logic into `humanoid_agent.py`.
2.  **Hardware Test**: Run the 60-case suite on physical Android devices.
3.  **End-of-Chain Logic**: Add code-level verification for the final turn of long chains.
4.  **Termux Verification**: Confirm the agent runs smoothly on ZA2232T6XT after the fix.

## [2026-05-13] Milestone: V4.0 Gemma 4 Vision Storyline & 60K Context
*   **Status**: ✅ Completed
*   **Achievement**:
    *   Verified **20-Image Batch Processing** in a single request (Success).
    *   Stabilized **60,000 Token Context Window** on Remote Endpoint.
    *   Achieved **82.39 TPS** (Internal) / **50.18 TPS** (Wall-clock) for complex vision tasks.
    *   Implemented **Storyline Logic Reconstruction** and **User Persona Psychological Analysis**.
*   **Insight**: Gemma 4 E2B's vision reasoning is robust enough for long-sequence replay and multi-step post-mortem analysis.

## 2026-05-13: Google Maps 搜索与拨号全线打通
- **教训**: 模拟器下 Google Maps 建议项触控失效，必须用 `adb shell input keyevent 66`。
- **发现**: XML Dump 可能会丢失底部 Sheet 节点，点击 'List view' 按钮可恢复。
- **成功路径**: 搜索 -> 回车 -> 切换列表 -> 点店名 -> 进入详情页 -> 点击 Call 按钮。
- **结果**: 成功跳转拨号盘，号码为 Sforno Pizzeria (+1 415-347-5881)。

## 2026-05-13: Intent-First Strategy Implementation & Robust Fallback
- **Progress**: Successfully implemented a high-performance coffee shop search and notification workflow.
- **Key Discovery**: Using "Call" button to trigger Dial Intent is more reliable than searching for phone numbers in raw UI text.
- **Lesson**: ADB shell often fails with non-ASCII characters in Intent extras. Switching to English bodies and proper shell quoting resolved the "unable to resolve Intent" errors.
- **Achievement**: Created `smart_coffee_agent.py`, a reusable script that bypasses UI exploration via Deep-links and Intent-based inter-app communication.

## 2026-05-14: Context Limit Debugging
- **Discovery**: Remote LLM (Gemma-4-e4b) context limit is confirmed to be **4608 tokens**.
- **Evidence**: Stress test script `test_context_limit.py` triggered 400 error: `n_keep: 5549 >= n_ctx: 4608`.
- **Conflict**: This contradicts the 60k token report from 2026-05-13. Possible causes: server restart with default config, or different model/backend instance being targeted.
- **Action**: Created `scripts/test_context_limit.py` for automated baseline verification.

## 2026-05-16: /task 连接问题诊断 & 端口对齐修复
- **问题**: 手机 App 发 `/task` 指令报"无法连接 Termux Relay"
- **根因**: `start_daemon_termux.sh` 里 `fuser -k 8766/tcp` 杀的是旧端口，但 `relay_server.py` 改为监听 8767 后未同步
- **修复**: `start_daemon_termux.sh` 端口 8766 → 8767，与 `relay_server.py` LISTEN_PORT 对齐
- **架构梳理**: 画了完整的 Mac→Win→Phone 链路图和端口全景表（见 artifact）
- **教训**: 端口配置散落在多个文件里（relay_server.py / start_daemon_termux.sh / RelayClient.kt / run_termux_server.sh），改一个地方必须全局 grep 确认一致性

### 简化重构完成
- **relay_server.py**: WebSocket server → stdlib HTTP server (POST /task, GET /status)，0 依赖
- **ChatViewModel.kt**: RelayClient.isConnected 判断 → HTTP POST localhost:8767/task，不再需要 WS 长连接
- **humanoid_agent.py**: 删掉 ws_poll()，语音插话已通过 Bridge HTTP /events 统一处理
- **消除端口**: 8768 (ws_channel server) 不再被 relay 依赖
- **简化前**: Chat UI → RelayClient.kt(WS:8767) → relay_server.py → ws:8768 → agent
- **简化后**: Chat UI → HTTP POST :8767 → relay_server.py → spawn agent

## [2026-05-16] 国际化支持 (Full English Agent)
- **Agent 全英文运行**: 实现了 `i18n.py` 模块化 Prompt 系统，将 `humanoid_agent.py` 和 `tool_layer.py` 中的所有 Prompt、日志及交互逻辑全部翻译为英文。Agent 现在的思考（Thought）和规划（Plan）默认使用英文，确保了对国际化用户的友好性。
- **Android UI 本地化**: 配合 Bridge 端的 `strings.xml` 迁移，实现了手机端 UI 与 Agent 端的语言同步。
- **代码清理**: 移除了 `humanoid_agent.py` 和 `tool_layer.py` 中残余的中文字符，修复了 AI 自动翻译引入的 `plan_lines` 变量未定义等逻辑漏洞（NameError）。
- **教训**: AI 在进行大规模代码翻译时容易产生变量名不一致的问题，必须通过静态扫描（grep/python 脚本）进行二次审计。
- **现状**: 目前 Agent 已实现“全英文思维”，但在 MD 文档层面保留中英双语，遵循“Append Only”原则。

## [2026-05-16] Gemini i18n 改动 Code Review & Bug Fix
- **🔴 Bug1: `pic_verify` NameError**: VERIFY_STITCH 模式下 `verify_images = [pic_verify]`，但 `pic_verify` 从未定义。改回 `[pic_before, pic_after]`。
- **🔴 Bug2: `_fix_array_types` 重复定义**: tool_layer.py 中 L52 和 L243 定义了两次同名函数，Python late-binding 导致弱版本覆盖强版本。删除重复定义。
- **🟡 Bug5-7: zh 模板缺变量**: `DECISION_SYSTEM`/`FINISH_CHECK`/`VERIFY_USER` 的中文版模板大幅简化，丢失了多个 `{placeholder}`。调用 `format()` 时 KeyError 被吞掉，返回原始模板字符串。已补齐。
- **✅ hermes-android 侧改动审查通过**: strings.xml 英中双语正确，`%1$s` 参数使用正确。
- **教训**: AI 做大规模翻译+重构时，中文版模板容易"偷懒"省略字段。必须写测试脚本验证 en/zh 模板占位符一致性。

## [2026-05-16] 仓库历史维护 (Repo History Compaction)
- **操作**: 压缩了最近的 3 个 Commit（WIP -> Bug Fix -> Docs Update）为单个功能提交 `feat(i18n): implement Gemini internationalization and fix related regressions`。
- **目的**: 保持主分支历史整洁，将 i18n 相关的增量开发与关键修复原子化。
- **状态**: ✅ 已完成并验证。

## [2026-05-16] i18n 策略纠正：最小化方案取代全量重写
- **问题**: Gemini 的 i18n 方案太重——把所有 working 的中文 prompt 全部重写成英文，创建了 263 行 `i18n.py` 维护两套模板，改变了 prompt 效果。
- **正确方案**: 恢复原始 inline 中文 prompt（已调好的不动！），只在 4 个 LLM prompt 末尾加一句 `"⚠️ You MUST reply in English"`。
- **改动量**: 4 行新增 vs Gemini 的 568 行删改。删除 `i18n.py`。
- **Android 端**: `strings.xml` 英中双语保留（那是标准 Android i18n，没问题）。
- **教训**: prompt 是经过调优的"模型指令"，不是普通文本——翻译 prompt ≠ 翻译代码注释。正确做法是保持 prompt 原样，只改模型输出语言。
- **Fix Overlay Display & Status Timing**:
  - Update `ChatViewModel.kt` to call `StatusOverlay.updateDashboard` with the user's task and `"STARTING"` status immediately when a task is submitted via the chat UI in Bridge mode. This ensures instantaneous visual feedback on the device.
  - Reverted changes to `humanoid_agent.py` and `humanoid_agent_adb.py` as they were unnecessary for the UI-driven Bridge mode experience.
- **Fix Task Failed TTS Bug**:
  - Identified an edge-triggered bug in `StatusOverlay.kt` where `lastMissionComplete` transitioning from `null` to `false` incorrectly triggered a "task failed" audio alert.
  - Updated the logic to only trigger failure feedback if the overall `state.status` contains `"EXHAUSTED"` or `"FAIL"`, accurately reflecting genuine execution failures rather than ongoing task steps.
- **Translate Overlay Strings**:
  - Translated hardcoded Chinese strings in `humanoid_agent.py` to English to maintain a clean English UI overlay:
    - `"任务刚启动，尚未执行动作。..."` -> `"Task started. Check screen and navigate if needed."`
    - `"所有子任务已 [x]"` -> `"All subtasks [x]"`
    - `"⏳ 正在思考任务规划..."` -> `"⏳ Thinking..."`
- **Feedback Loop to Chat UI**:
  - Implemented a callback mechanism in `StatusOverlay.kt` to send the final `scratchpad` contents (the agent's findings) back to the Chat UI via `ChatEventBus` when a task reaches a terminal state (`SUCCESS`, `FAIL`, or `EXHAUSTED`). This closes the interaction loop for UI-driven tasks.
- **Task Initialization Standardization**:
  - Added a mandatory `get_device().home()` command right before the main execution loop in `humanoid_agent.py` and `humanoid_agent_adb.py`. This ensures every task starts from a clean, predictable state (the Android home screen), reducing context errors in the very first step.

## [2026-05-17] On-Device LLM Activation & Dynamic Timeout Hardening
- **诊断背景**: 在更换为端侧大模型 `Gemma-4-E2B-it` 后，Agent 在结果核验 (VERIFICATION) 阶段因 `<ERROR> HTTPConnectionPool(host='127.0.0.1', port=8080): Read timed out. (read timeout=60)` 异常崩溃退出。
- **根因分析**:
  1. **端侧进程未就绪**: 最初手机上的大模型 API 服务 App `com.google.aiedge.gallery.openai` 进程并未运行，导致端口 8080 挂死。我们通过 adb 启动该 App (PID 18716) 并在 IPv6 双栈 (`tcp6` 表) 成功观测到 `LISTEN` 状态。
  2. **Prefill 计算超时**: 核验 (VERIFICATION) 阶段传入的 UI 元素清单 (BEFORE UI inventory) 和 UI Diff 信息非常庞大，在手机端物理硬件上进行本地预填充计算 (Prefill) 和首 Token 生成 (TTFT) 极耗时间，轻易超过了原代码中硬编码的 60 秒网络超时时限。
- **修复与重构**:
  - 在 `humanoid_agent.py` L302 中，将原本写死的 `timeout=60` 升级重构为动态环境变量读取加超长兜底模式：`timeout=int(os.getenv("LLM_TIMEOUT", "300"))`。默认给予 5 分钟 (300 秒) 的充足响应时间，并允许通过外部环境变量无缝调节。
- **验证与审查**:
  - 成功执行 `python3 tests/test_inventory.py` 单元测试，确认核心 XML 解析与语义节点提取管道 100% 正常。
  - 调用 `qwen` 智能审查助手 (`/opt/homebrew/bin/qwen --auth-type openai -m gpt-4o-mini`) 对此项改动进行了深度代码审查，审查结论为“安全、正确、符合动态配置的最佳实践”。
- **教训与经验 (Lessons)**:
  - **端侧大模型的特殊性**: 手机端侧推理与云端大模型服务有着本质的延迟差异。不仅首词延迟较高，Prefill 速度也受算力限制，任何 LLM 客户端在对接端侧大模型时都必须极大幅度提高网络超时限制（建议 ≥ 3 分钟）。
  - **IPv6 盲区**: 许多现代 Android APP（包括 Model Studio App）创建 socket 默认绑定 IPv6。使用传统的 `cat /proc/net/tcp` 查找 IPv4 监听会造成“服务未就绪”的假象，必须去 `/proc/net/tcp6` 探查真实现状。

## [2026-05-17] Motorola moto_freezer Discovery & Permanent Background Exemption
- **新痛点诊断**: 在验证过程中发现部分步骤（如第 3, 4, 5, 7, 8 步）在发送 DECISION 请求后刚好约 5.5 秒即报出 `500 Server Error`，而另外一些请求则能耗时 118 秒完美返回 200。
- **根因剖析 (`moto_freezer` 冻结机制)**:
  - 手机设备为 **Motorola (摩托罗拉)**，其魔改系统内置了极其激进的后台管控服务 **`moto_freezer` (SmartFreeze)**。
  - 由于 Agent 在前台自动操作其他 App (如 Airbnb/Maps)，推理服务 App `com.google.aiedge.gallery.openai` 必定处于后台。
  - `moto_freezer` 在检测到该 App 处于后台后，会强行**挂起/冻结 (Freeze) 其所有 CPU 线程**。此时发送 HTTP 请求，由于接收端线程被暂停，会瞬间发生丢包或超时并返回 500。
- **永久修复方案 (免重启即时生效)**:
  - 通过 ADB 强制将大模型 App 设为**后台白名单 (RUN_IN_BACKGROUND allow)** 并加入 **DeviceIdle 电池优化白名单**，彻底豁免其后台冻结权：
    1. `adb shell cmd appops set com.google.aiedge.gallery.openai RUN_IN_BACKGROUND allow`
    2. `adb shell dumpsys deviceidle whitelist +com.google.aiedge.gallery.openai`
  - 重启 App 后验证，端口 `8080` 保持持久健康监听，彻底解决后台间歇性“秒退 500”报错。


