# Changelog

## [Unreleased]

### Added
- 集成了高性能的 Bridge Android 控制器，支持 JSON UI 树解析。
- 在 `intent_library.py` 中新增并验证了日历日程、导航、设置等多个语义跳转模板。
- 确立了 Bridge + ADB 的“双轨制”传送策略，解决了权限受限场景下的自动化兜底。
- **全英文 Agent 支持**: 引入 `i18n.py` 管理多语言 Prompt。
- 所有的 Agent 思考逻辑、规划步骤及控制台日志均已切换为英文。
- `humanoid_agent.py` 增加了对 `i18n.get_prompt` 的全面调用。

### Changed
- 优化了 `BridgeClient` 的 Intent 发送逻辑，支持多维 Extras 参数。
- 改进了截图流程，支持自动隐藏 Bridge 悬浮窗以保证视觉模型识别率。
- 清理了核心逻辑代码中的所有中文注释。
- 优化了 `tool_layer.py` 的架构，按需导入 `i18n` 以减少模块耦合。

### Fixed
- 修复了日历 Intent 缺少 `dataUri` 导致无法唤起 App 的问题。
- 解决了 `teleport` 工具在处理非 JSON 参数时的解析偏差。
- 修复了 `humanoid_agent.py` 中因变量名 `plan_lines` 未定义导致的核验步崩溃问题。
- 修复了 `tool_layer.py` 中 `open_app` 报错信息硬编码为中文的问题。
- 解决了多处变量命名不一致（如 `done_str` vs `done_str_v`）导致的逻辑隐患。
- 🔴 修复 `pic_verify` NameError：VERIFY_STITCH 模式下引用未定义变量，改回 `[pic_before, pic_after]`。
- 🔴 修复 `_fix_array_types` 重复定义：tool_layer.py 弱版本覆盖强版本，删除重复定义。
- 🟡 修复 zh 模板缺占位变量：`DECISION_SYSTEM`/`FINISH_CHECK`/`VERIFY_USER` 中文版补齐 `scratchpad_len`/`apps_str` 等字段。

## 2026-05-16: Relay 架构简化
- relay_server.py: WS → HTTP (stdlib), 去掉 websockets 依赖
- /task 链路: 3层(WS+WS+subprocess) → 1层(HTTP+subprocess)
- 消除 ws:8768 作为 relay→agent 通信的中间层
- ChatViewModel.kt: RelayClient WS → OkHttp POST

## [2026-05-16] Repository Maintenance
- **Git Strategy**: Compacted last 3 commits into a single atomic feat commit to clean up the i18n migration history.
- **Branching**: Created `backup-i18n-refactor` as a safety checkpoint before the destructive rebase.

## [2026-05-17] On-Device LLM & Timeout Optimization

### Fixed
- **端侧大模型超时修复**: 将 `humanoid_agent.py` 中向本地大模型 API 发送请求的硬编码网络超时时间 `timeout=60` 升级为 `timeout=int(os.getenv("LLM_TIMEOUT", "300"))`。有效解决了端侧本地 Gemma-4-E2B-it 大模型在处理庞大 UI 元素清单上下文时发生“Prefill 超时”导致 Agent 崩溃的问题。
- **网络监听排查对齐**: 诊断了 `com.google.aiedge.gallery.openai` 运行后未能通过 IPv4 监听 8080 端口的问题，确认其工作于 IPv6 双栈任意地址 (`:::8080`) 并成功建立 TCP 连接。
- **后台冻结永久豁免 (Motorola `moto_freezer`)**: 通过 ADB `appops` 和 `deviceidle` 强行赋予本地推理服务 App 全天候后台活动白名单权限，彻底终结了进程在后台运行时被系统冻结（Freeze）导致间歇性爆出 `500 Server Error` 的重大运行隐患。

### Changed
- **LLM 请求超时动态化**: 支持通过 `LLM_TIMEOUT` 环境变量灵活调节大模型请求的超时配置，提高架构弹性。


