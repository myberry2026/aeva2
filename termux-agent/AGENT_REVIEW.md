# humanoid_agent.py 架构问题清单

`humanoid_agent.py` 当前是 **Do → Verify** 双 LLM 调用循环（每步 2 次 vision 推理）。整体方向 OK——每步都有 ground truth 反馈，比纯 ReAct 单链路稳——但存在以下问题。

## 已修（2026-05-10）

| # | 问题 | 修复方式 |
|---|---|---|
| 1 | Verify 只看 after 单图，prompt 让模型"对比 before/after" 但实际只传一张 | `agent_call` 改为接受图像列表；verify 同时传 before+after，可选拼接为单张大图 |
| 2 | `open_app` 默认硬编码 `com.google.android.apps.maps`，goal 也写死 | 启动时 `cmd package query-activities` prefetch launcher 入口包名，注入决策 prompt 让模型自选；CLI 接受任意 goal |
| 3 | 连续失败死循环，没有兜底 | `consecutive_fails` 计数，>=3 触发 home + 强制重规划提示 |
| 4 | finish 无验证，模型一声明就 break | 加 FINISH_CHECK 二次核验门，不通过继续 |
| 5 | 元素 ID 跨步重排但模型可能引用上一步 ID | prompt 明示"ID 仅本步有效，跨步用 label" |
| 6 | 起始环境不确定（不一定在目标 app） | 初始 `last_verify_result` 显式提示模型先核对环境，必要时 open_app |
| 7 | `remaining_gap` 每次复读总目标全文，模型不知道还差几步 | verify schema 加 `task_complete: bool`（布尔难糊弄）；prompt 强约束：remaining_gap 只写"还没做的具体动作"，禁复述目标 |
| 8 | 任务完成后停不下来：模型不主动 finish，verify 也没机制触发退出 | verify 自报 `task_complete=true` 时**立刻**调用 `run_finish_gate`，跳过下一轮决策；通过即 return |
| 9 | accomplishments 被污染（模型把"已成功返回联系人主页"这种与目标无关的成功也塞进来）| prompt 强约束：accomplished_now 只列"实质推进总目标"的里程碑；普通页面跳转/误回退**必须填 []** |
| 10 | finish gate 内联在主循环，自报 finish 与 task_complete 自动触发会重复一份 | 抽出 `run_finish_gate(step, goal, accomplishments, trigger_reason)` 复用 |
| 11 | 无 Plan 层（架构性），导致多子目标任务易耗尽预算 | 实现 `plan_call` 任务拆解 + 状态清单（Checklist）跟踪；每步 verify 强制更新 checklist 状态 |
| 12 | 缺乏可观测性，难以回溯调试与 Prompt 迭代 | 集成 Langfuse；实现 Prompt 托管（PLAN/DECISION/VERIFY/FINISH）；加入 Session 与 Generation 跟踪 |

## 已修（2026-05-10）— 早期 round

| # | 问题 | 修复方式 |
|---|---|---|
| A | `keyevent 29 --metaState 28672` 顺序错，Ctrl+A 不生效 | 改为 `--metaState 28672 29` |
| B | 两处裸 `except:` 吞掉所有错误 | 拆成 `RequestException` / `JSONDecodeError` / `ParseError`，写日志写黑匣子 |
| C | `decision['id']` 不校验越界 | `_resolve_elem` 类型+范围校验 |
| D | `verification['xxx']` 直接取 key，缺一就 KeyError | 全改 `.get()` 加默认值 |
| E | 决策返回空时 `continue`，下一轮上下文不变 → 死循环 | `last_verify_result` 写明失败原因，下一轮模型可见 |
| F | `rich_history` 死变量 | 删除 |
| G | 硬编码屏宽 1075 | `wm size` 动态拿，用 `SCREEN_W * 0.99` |
| H | text 仅替换空格，特殊字符注入 shell | `_escape_adb_text` 转义 `& < > ' " ( ) \| ; \` $ * ? [ ] { } ~ #` |
| I | 40 次串行 `keyevent 67`（约 4s） | 单条 shell `for i in $(seq 40); ...`（~0.3s） |

## 未修 / TODO

按改动量从小到大：

1. **跳过 verify for 系统动作**：`open_app` / `home` / `wait` 这类动作效果显而易见，verify 是纯浪费 token。已部分实现，可继续细化。
2. **元素清单噪声**：当前过滤 `< 5px` 和 `> 99% 屏宽` 但不分层级，重叠 clickable 容器会塞满清单。可考虑 (pos, label) 去重，相同位置只留最具体的 label。
3. **固定 `sleep(4)` 太僵**：地图加载 8s 不够，菜单切换 0.5s 又过头。改进方向：UI 稳定性轮询——连续两次 dump 哈希一致即视为稳定，否则继续等。

## 设计原则备忘

- **Do→Verify 整体保留**——反馈循环是 Agent 稳定的关键
- **通用型优先**：不要在代码里硬编码任何具体 app/任务，所有项目特异性走参数或 prompt 注入
- **黑匣子完整**：所有 LLM 调用、错误、兜底动作都写 `logs/agent_debug.log`
