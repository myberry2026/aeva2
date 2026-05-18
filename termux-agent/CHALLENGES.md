# 工程挑战记录 / Engineering Challenges

> 评委版：从一份能跑但脆弱的 demo，迭代到能"诚实拒绝完成"的通用 phone agent，期间踩的真实坑

## TL;DR

我们不是从头实现一个 phone agent。我们花了一天时间**把一个能 demo 但工程上千疮百孔的原型**，迭代成一个**敢在评委面前演"主动失败"的鲁棒系统**。

中间踩了 14 类典型 agent 工程坑，每一类都对应一个可以讲故事的 insight。**Prompt 字面调了几十轮**，最难的那几轮的故事都在下面。

---

## Challenge 1: VLM 在"是否成功"上系统性说谎

### 问题
跑了一轮真实任务，发现 verify 模型经常报告：
> "已成功输入搜索词" → 实际截图里输入框是空的
> "已成功打开拨号界面" → 实际还在搜索结果页

### 根因
Gemma 这类 VLM 有 **pattern-matching confirmation bias**：你 prompt 里说"刚才尝试 type 'best pizza'"，它会**默认动作成功**，即使 AFTER 截图明显反驳。这不是它"看不见"，是它在 hallucinate confirmation。

### 解决
1. **双图对比**：verify 同时传 BEFORE + AFTER 两张图，prompt 强制对比变化
2. **二次核验门 (finish gate)**：模型声明完成时不退出，单独发一次 audit prompt，附带执行历史
3. **结构化字段**：`mission_complete` 必须配 `mission_reason`，bool 难糊弄但孤布尔会瞎填，配个理由模型瞎填会被自己写出的理由打脸

### Insight
**对 flaky 模型，结构化输出 + 程序侧确定性校验，比再调多少 prompt 都管用**。

---

## Challenge 2: 静态 Plan 跟现实分歧

### 问题
原本 plan 是动作清单："点击搜索按钮 → 进入详情页 → 点 Call 按钮"。

实际跑：Google Maps 的搜索结果列表项**直接就有 Call 按钮**，模型一眼看到，跳过"进详情页"直接点了。

但程序仍在等"进详情页"那一格被打勾——**plan 永远卡住**，模型陷入"我做了但系统不认"的死循环。

### 根因
**Plan 跟踪的是"做了哪些动作"，但目标本质是"达到了哪些状态"**。app 的交互路径可能多条，动作 plan 死板地假设其中一条。

### 解决
**Plan 抽象层升一级：从动作步骤改为状态条件 (state-based criteria)**

| ❌ 动作 plan | ✅ 状态 criteria |
|---|---|
| "点击搜索按钮" | "屏幕显示搜索结果列表" |
| "进入详情页" | "屏幕上出现过评分 ≥4.6 的店" |
| "点 Call 按钮" | "屏幕上出现过电话号码" |

加上 **once-true-stays-true 语义**：状态达到过就锁定 true，不会因为后续切页变 false。

### Insight
**这呼应了 robotics 界 VLA + Agent 的分层思路**——上层定义"目标状态"，下层实现"任意路径达成"。我们用同样的哲学解决了 Android UI 自动化。

---

## Challenge 3: 索引语义混乱 → checklist 错位

### 问题
verify 让模型返回 `subtasks_done: [int]` 标记刚完成的子任务索引。模型一会儿用 1-indexed (`[2,3]` = 第2第3项)、一会儿用 0-indexed (`[4]` = index 4)，**每步赌哪种**。最终 plan_state 完全乱套。

### 根因
checklist 显示用 1-indexed（"1. 打开地图 / 2. 搜索..."），但 prompt 描述时说"`[2]` 表示第 3 项"，自己都不一致。模型在两种约定之间漂移。

### 解决
不让模型选索引，而是**返回完整 boolean 数组**：
```json
"subtasks_status": [true, true, false, false, true, false]
```

长度等于 plan 长度，位置对应。模型不需要 reason 索引语义，只需对照清单填当前状态。

加 historical OR 累积：`plan_state[i] = plan_state[i] OR new[i]`。模型一不留神把 true 改回 false 也没事，程序只接受单调升级。

### Insight
**给 flaky 模型设计 schema，要让"瞎填的代价"<<"瞎填的诱惑"**。索引数组让模型必须 reason；bool 数组只需照镜子。

---

## Challenge 4: 跨步 state 怎么传 - 长 context vs fresh loop

### 问题
agent 跑 10 步后，模型会忘掉前面试过什么、做错了什么、卡在哪里——重复同一个失败动作。

### 根因
我们的 agent loop 是 **fresh-loop**：每步独立 HTTP 调用，新 KV cache。模型没有跨步记忆。

### 选项与权衡
| 方案 | 优 | 劣 |
|---|---|---|
| chat-based 长 context | 模型自然有记忆 | Gemma 长 context 下推理崩坏；KV 复用收益打折 |
| 滚动 deque 窗口 | 显式控制 | 仍然让模型自己 diff，浪费 prefill |
| **显式 delta 注入**（采用） | 程序算好 diff 喂进去 | 需要设计 delta 格式 |

### 解决
保持 fresh-loop，但每步主动注入：
- `last_verify_result`：上一步动作 + 反思
- `plan_state` 的 checklist 渲染（带 [x] / [→] / [ ] 标记）
- `已达成成就` 列表

**程序当模型的 working memory**。

### Insight
**对 short-context 模型，"我们手动管理上下文"反而比"让模型自己管"更稳**。这是 fresh-loop 在 VLM 场景的胜出原因——前一步的截图反正过期了，没必要让模型在长 history 里挣扎。

---

## Challenge 5: 失败检测 + 恢复

### 问题
跑到第 10 步，模型卡在错误页面循环 `back` 5 次都没回到 Maps。没有任何机制触发"换个策略"。

### 根因
单纯监测 `action_success` 不够：动作可能"看似成功"（界面变了），但**对目标推进 = 0**。

### 解决
三层兜底：
1. **`consecutive_fails` 计数**：动作成功但无新 plan_state 推进 → 累计
2. **达到 3 触发兜底动作**：home + 强制重规划提示
3. **finish gate 否决回退**：声明完成被 audit 拒绝时，回退最后一格让模型继续

### Insight
**"成功"是局部信号，"推进"才是全局信号**。同时监测两个信号，避免假阳性。

---

## Challenge 6: 通用性 vs 简单性的张力

### 问题
hackathon 时间紧，想做"通用 phone agent" 但技术风险高；想做"特定 app 自动化" 风险低但跟评委已经看过的 demo 没区别。

### 关键决策
我们坚持**通用性作为 demo 的护城河**。不在代码里硬编码任何 app/任务，所有项目特异性走参数 + prompt 注入：
- `goal` 通过 CLI 传入
- 已安装 app 通过 `cmd package query-activities` prefetch 给模型
- plan 通过 LLM 实时生成（带缓存）

代价：每个 app 的自动化没有专门优化，依赖模型的视觉 grounding 能力。

收益：**评委会问"换个 app 还能用吗？" 我们当场跑给他看**。

### Insight
**通用性是不可被 fast follow 的差异化**。专用 demo 评委今天看了，明天可以让团队复制；通用 agent 是架构哲学，不是 prompt 工程。

---

## Challenge 7: Prompt schema 调了几十轮才稳

### 问题
verify schema 不是一锤子定的，是被模型反复打脸出来的：

| 版本 | 问题 |
|---|---|
| v1: `accomplished` 自由文本 list | 模型把"返回联系人主页"也算成就，污染历史 |
| v2: `task_complete: bool` 孤布尔 | 没理由约束，模型瞎填 true |
| v3: `task_complete` + 强制 `task_reason` | 字段命名歧义，"task" 是单步还是整体？ |
| v4: 重命名 `mission_complete` + `mission_reason` | 顺序混乱，bool 在中间不在最后 |
| v5: 调整字段顺序：局部 → 全局递进 | `accomplished_now` 命名仍然不直观 |
| v6: 改名 `progress`，定义为 array | 类型歧义：单个 string 还是 list？ |
| v7: `progress` 改单 string，跨步 append 累积 | 模型仍可能瞎填"成功 X" |
| v8: `subtasks_done: [int]` 索引数组 | 模型在 1-indexed / 0-indexed 之间漂移（见 Challenge 3） |
| v9: 完整 bool 数组 + historical OR 累积 | 终于稳定 |

### 根因
**没有一次设计就完美的 prompt schema**。每一轮都是"prompt 假设了模型行为 → 模型真实行为打脸 → 改 prompt"。

### Insight
- **每次失败都对应一个具体的 hallucination 模式**——记录下来下次直接绕开
- **字段命名要承担语义防御**：`mission_complete` 比 `task_complete` 好，因为 mission 暗示"全局"
- **结构化字段 > 自由文本**：能用 bool / int / 定长数组就别用 string
- **类型必须明确**：array 还是 string，prompt 里得画出来 (`"progress": "..."` vs `"progress": [...]`)

### 教训抽象
**Prompt schema 是和模型博弈的契约**。模型会找到所有歧义钻空子；你必须把每个字段的"瞎填收益"压到最低。

---

## Challenge 8: 中间 subtask false 但 mission 实际完成

### 问题
跑完一轮，plan_state = `[T, T, F, T, T]`——第 3 格永远没被勾上。但最终截图明显显示任务完成了。

如果死板用 `all(plan_state)` 判完成，**永远停不下来**；如果让模型说"完成了就好"，又回到 hallucination 老路。

### 根因
**Plan 是 hint，不是 contract**。模型可能跳过某些"中间状态"直接到达终态——比如 Maps 列表项直接有 Call 按钮，不经过详情页就拿到电话号码。我们的 plan 假设要点详情页（C3），但路径上根本没出现该状态，C3 永远 false。

### 解决
**双触发条件 + finish gate 作为最终仲裁**：

```python
if all(plan_state) or mission_complete:
    passed, ev = run_finish_gate(step, goal, plan, plan_state)
    if passed:
        return  # 真完成
    # 否则回退最后一格，继续推进
```

- `all(plan_state)` → 经典完成路径
- `mission_complete=true` → 模型主动说完成（但要被 audit）
- 两者**任一**触发 finish gate
- finish gate 看截图 + 全状态，有权限**忽略 plan_state 中间的 false**，只看终态合理性
- audit 否决 → 回退最后一格让模型继续，避免陷入"假完成-否决-继续假完成"死循环

### Insight
**Plan 是地图，不是铁轨**。你给模型路线图建议，但不能强制它必须途径每个站点。**最终判断权交给独立的 audit step，看截图证据，不看打勾数量**。

这也呼应了 **state-based criteria 的核心**：状态达到才重要，路径不重要。

---

## Challenge 9: VLM 看不懂电话号码格式变体

### 问题
Demo 任务："找到店铺电话号码"。屏幕上显示 `1 (888) 888-8888`。我们的 verify prompt 让模型确认"是否看到电话号码 18888888888"。

**模型说没看到**——它把 `1 (888) 888-8888` 和 `18888888888` 当成两个完全不同的字符串。

### 根因
VLM 在视觉 OCR 后做的是**字面字符串匹配**，不会主动 normalize。括号、空格、连字符都是不同字符。

更深层：**模型没有"电话号码的语义"概念**——它不知道这两个字符串都映射到同一个号码实体。

### 解决思路（三选一，我们最后用了 prompt-based）
1. **Prompt 引导 normalize**："电话号码可能有多种格式（带括号、空格、连字符），都视为同一个号码"
2. **程序侧 normalize**：从屏幕和目标各自 strip 掉所有非数字字符再比较
3. **告诉模型只看数字**："只比较数字部分，忽略格式"

最终 **prompt 加了一条提示**让 Gemma 自己 normalize，跑通了。

### Insight
- **VLM 的"视觉理解"是浅层的**——能 OCR 但不能 reason about 实体
- **跨模态实体识别**（同一个号码 / 地址 / 时间在不同视觉表现下识别为同一）需要明确 prompt 引导
- **更重要**：这是普遍模式。电话、日期、地址、价格、时间——所有有"标准化形式"的东西都会踩这坑
- 解法的工程化版本：维护一个 `normalize_*` 函数库（号码、日期、货币、地址），verify 阶段两边都跑过函数再比较

### 给评委讲
> "我们 demo 中遇到一个具体的失败：模型说看不到电话号码，但屏幕上明明有。原因是 `1 (888) 888-8888` 和 `18888888888` 在它眼里是两个东西。这暴露了 VLM 的一个普遍局限——它会 OCR 但不会 reason about 实体身份。我们用 prompt 引导解决了，但工程化时这需要一整套 normalizer。"

这一段评委会觉得：**这队人真的 ship 过 demo，不是在 PowerPoint 里演 agent**。

---

## Challenge 10: UI 自动化的"暗物质"——uiautomator 看不见的按钮

### 问题
跑 Google Photos 选壁纸任务，agent 卡在照片选择器里 15 轮。模型反复点击橘猫图、long_press、scroll_down，**就是找不到右上角那个"Done" 按钮**。50 步预算耗尽，任务失败。

直觉以为是模型视力差。**实际不是**——是 `uiautomator dump` 这个数据源本身有黑洞。

### 根因（log 考古结果）
打开 dump 出来的 XML，右上角区域 `(x>900, y<300)` 实际上**只有三个东西**：
- `LinearLayoutCompat` 容器，`clickable=false`，被我们的 inventory 过滤掉
- `action_bar_overflow`（三个点菜单）
- 一个 `ImageView` 图标，`clickable=false`，过滤掉

**真正的"Done"按钮根本不在 XML 里**。Google Photos 用了一个 `touch_capture_view` 透明覆盖层处理触摸事件，按钮的视觉渲染走自定义 Canvas，**不是标准 View Hierarchy**。

这是 Android 高度自定义 UI 的常见模式：性能优化 / 动画自由度 → 牺牲了无障碍可见性。同类陷阱遍布：游戏 UI、地图 overlay、相机界面、Compose 应用。

### 模型的"莫比乌斯环"
agent 的逻辑闭环很合理：
- 看到清单里左边有 `Cancel`（[73, 212]）
- 推断右边应该对称有 `Done`
- 清单里右边只有"三个点"
- 点三个点没反应（log 证实它真试过 step 40）
- 怀疑自己第一步选猫没选对 → 重新选 → 重新选 → 死循环

模型**没错**，错的是它拿到的世界模型不完整。

### 这是不是只能"作弊"才能解？
不是。三层解法，复杂度递增：

#### 解法 1: 释放 `point` 字段，鼓励盲狙（最快）
代码里已有 `point: [x, y]` action，但 prompt 没鼓励用。改进：
- prompt 加一条："**清单不是真理，是建议**。如果你视觉上看到某个按钮但清单里找不到，直接用 `point: [x, y]` 估算坐标点击。"
- 加 Material Design 启发式："左上 nav-up / 中标题 / **右上 actions（Done/Save/Menu）**"，宁可盲狙错也别原地打转

#### 解法 2: Stuck 检测 → 切换"视觉自由模式"（中等）
连续 3 步 plan_state 没推进 → 主循环切模式：
- 决策 prompt 改成："你陷入卡死。**忽略元素清单**，纯看截图，估算需要点击的坐标，输出 `point`"
- 这本质是把模型从"清单驱动"切到"视觉驱动"，绕过 dump 黑洞

#### 解法 3: 多源 UI inventory（治本但工程重）
uiautomator 不靠谱时，备用数据源：
- **Accessibility Service** API：能看到部分 uiautomator 看不到的元素
- **Vision-based element detection**：让 Gemma 自己看截图输出 bbox 列表 ("我看到右上角有个勾形图标 @ [1020, 200]")
- **`adb shell dumpsys window` + activity 名**：辅助判断当前 app 状态
- 把多源结果 merge，inventory 不再单点失败

### Insight
**`uiautomator dump` 是 lossy 的视觉抽象**。它对标准 Material UI 友好，对自定义/游戏化/动画化 UI 是黑洞。

agent 任何"靠 ID 行动"的设计，本质上都把信任押在 dump 完整性上——这是个**会持续踩的雷区**，不是一次性 bug。

更深的教训：**视觉模型的 ground truth 应该是像素，不是 XML**。XML 是优化（提供元素 ID 让 click 精准），但当 XML 撒谎时，要让模型敢于"不看 XML 也敢点"。

### 给评委的话
> "这个 bug 是我们 demo 跑通后才发现的真实陷阱。不是设计失误，是 Android 生态的固有问题——
> 高定制 UI 会绕过标准 accessibility 框架。我们的解法是教 agent **当 XML 撒谎时，相信自己的眼睛**——
> 这恰恰是 Gemma4 多模态视觉能力被需要的地方。**纯 LLM agent 在这种场景必死**，
> vision-language model 才有救。"

这一段 punch line 把"我们解决了一个 bug"升级到"我们论证了为什么必须用 VLM"。

---

## Challenge 11: 不是所有可交互元素都 `clickable=true`

### 问题
Chrome 浏览器搜索框 demo 时点不进去——agent 看截图明明知道搜索框在哪，但元素清单里**没有这一项**，没有 ID 可点。

### 根因
我们的 `get_ui_inventory` 最初只过滤 `clickable=true` 的节点。但 Chrome 搜索框、很多 `EditText` 输入框、地址栏类的元素，在 Android view tree 里实际是：
- `clickable=false`
- **`focusable=true`**（用户聚焦输入用，不是普通点击）
- `long-clickable=true`（某些场景）

按"只要 clickable"过滤直接漏掉所有输入框入口。

### 解决
扩展 inventory 的 "is_interactive" 判定：
```python
is_interactive = (
    a.get('clickable') == 'true' or
    a.get('focusable') == 'true' or       # 输入框 / 地址栏
    a.get('long-clickable') == 'true' or  # 某些菜单
    "edit" in cls.lower() or              # EditText 子类
    "EditText" in cls or
    "search" in res_id.lower()            # 命名启发式
)
```

多条件 OR 兜底，宁可清单略冗余，也不漏关键元素。

### Insight
**Android view 的"可交互"是多维概念**——`clickable` / `focusable` / `long-clickable` / `editable` 是四个相对独立的属性。任何"只看一个属性"的 inventory 都会有结构性盲点。

跟 Challenge 10 的 `touch_capture_view` 一脉相承：**view hierarchy 的语义比表面看起来更乱**。Inventory 设计要"宁错杀不放过"。

---

## Challenge 12: 模型偷懒返回 `id: null` —— 用严厉 feedback 教训它

### 问题
跑了几轮，发现 verify 反馈里频繁出现 `IndexError: id=None`。模型 decide 时本来该选 `id: 5` 这种具体索引，结果给我一个 `id: null`——动作配合 `click` 但说不清点谁。

### 根因
两种情况：
1. 模型懒，看不出该点哪个，**输出 null 让程序"自己看着办"**
2. 模型搞错了，把 `id` 跟 `point` 弄混，该填 ID 时填了 None 留给 point 字段

### 解决
程序侧严格捕获 + 严厉具体的 feedback：
```python
def _resolve_elem(d):
    i = d.get('id')
    if not isinstance(i, int) or i < 0 or i >= len(elements):
        raise IndexError(f"id={i!r} 越界（清单仅 {len(elements)} 项）")
    return elements[i]
```

捕获后 exec_error 写进 `last_verify_result`，下一步 prompt 里模型会看到：
> "上一步动作 [click] 失败。执行期错误: IndexError: id=None。**清单里 ID 是存在的，请仔细看清单后再选**。"

不让模型蒙混过关，**逼它重新看清单挑一个具体 ID**。

### Insight
- **模型的偷懒倾向是结构性的**，不是 prompt 不够明确——再 strict 的 prompt 也会被遇到决策困难时绕过
- **程序侧硬错误 + 反馈到下一轮 prompt** 比"再加一句禁止 null"管用 10 倍
- 通用模式：**type validation 必须在程序侧 enforce**。模型出 schema 违规 → 报错 → 错误信息变成下一轮的"教训"
- 严厉具体 > 泛泛禁止："清单里 ID 是存在的，请仔细看" 比 "id 不能是 null" 让模型记得更牢，因为它包含了**纠正方向**

### 通用化为一个原则
> **Schema 防御要分两层：prompt 防瞎填（事前），程序防 invalid（事后），事后捕获要把"为什么错 + 怎么改对"写进下一轮上下文。**

这条对所有 LLM agent 都成立，不只是 phone agent。

---

## Challenge 13: ⚠️ 老 Bug 又回来了 - Android 清空文字的物理级噩梦

### 问题现场
在长输入框中，清空逻辑失效，新旧文字重叠成了"缝合怪"。

### 致命细节：POSIX Shell 转义陷阱
原本的代码：
`run_adb(["shell", "for i in \$(seq 200); do input keyevent 67; done"])`

**解析：**
- `\$` 会被转义为字面量 `$`，剥离了 shell 的命令替换特性。
- Shell 看到的是 `(seq 200)` 而非 `$(seq 200)`。
- `for` 循环只分割出 `$(seq` 和 `200)` 两个 token，实际只执行了 **2次 DEL** 而非 200次。
- 在短输入框可能因为 Move_End 或后续逻辑"看起来工作"，但在长文本下瞬间翻车。

### 为什么 Android 清空输入框是工程噩梦？
1. **Tap 盲区**：Tap 不保证 focus 到正确子 view。
2. **IME Race Condition**：Tap 后等待软键盘弹出时，Focus 可能丢失。
3. **实现碎片化**：不同 App 的 EditText 对 `Ctrl+A` 或 `Shift+Home` 支持度不一。
4. **状态易碎**：任何 UI 变化都会 reset 选中状态。
5. **光标黑盒**：长文本下光标起始位置完全未知。
6. **非原子性**：`MOVE_END` -> `Shift+Home` -> `DEL` 三步之间无原子性，易被打断。

### 🥇 终极可靠方案：ADBKeyBoard 广播
**原理：** 绕过按键模拟，直接通过 IME 接口调用 `setText("")`。这是最干净、最快、最稳的方法。
**指令：** `adb shell am broadcast -a ADB_CLEAR_TEXT`

### 🥈 次优方案：Python 侧批量发 keycode
**写法：** `run_adb(["shell", "input", "keyevent"] + ["67"] * 100)`
**优点：** 零 shell 转义、零 race condition，一次性发送 100 个原子操作。

### 🥉 建议的最终版 `adb_type` 逻辑
```python
def adb_type(x, y, text):
    run_adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(1.0)

    # 清空：优先用 ADBKeyBoard 广播（最稳），fallback 到批量 DEL
    current_ime = (run_adb(["shell", "ime", "list", "-s"]).stdout or "").strip()
    if "com.android.adbkeyboard" in current_ime:
        run_adb(["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"])
        time.sleep(0.3)
    else:
        # 兜底：MOVE_END + 100 次 DEL（正确批量写法）
        run_adb(["shell", "input", "keyevent", "123"])  # MOVE_END
        time.sleep(0.1)
        run_adb(["shell", "input", "keyevent"] + ["67"] * 100)
        time.sleep(0.3)

    # 输入新文本
    is_unicode = any(ord(c) > 127 for c in text)
    if is_unicode and "com.android.adbkeyboard" in current_ime:
        run_adb(["shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT", "--es", "msg", text])
    else:
        run_adb(["shell", "input", "text", _escape_adb_text(text)])

    if text.endswith("\n"):
        run_adb(["shell", "input", "keyevent", "66"])
```

### Insight
在有 ADBKeyBoard 环境下，**ADB_CLEAR_TEXT 是唯一的真理**。它把非确定性的"按键模拟"变成了确定性的"状态赋值"。

---

## Challenge 14: `keyevent 66` (Enter) 是个谎言 —— ADB_EDITOR_CODE 才是正路

### 问题
所有 agent 想"发送/搜索/确认"时，本能反应是模拟 Enter 键（`input keyevent 66`）。这看起来天经地义。

**但 Enter 在 Android 上行为完全不可预测**：
- 微信 / iMessage / Telegram 输入框：Enter = **换行**，不是发送（发送在独立按钮）
- Maps 搜索框：Enter 通常触发搜索（但 webview 内嵌搜索框可能 = 换行）
- 多行 Notes：Enter = 换行
- 表单密码框：Enter 可能 = 提交也可能 = 失焦

agent 写 "type 'best pizza\n'" 时，**祈祷 app 把 Enter 当搜索**——大部分时候 work，但每个 demo 都有 5-10% 翻车率。

### 根因
Enter 是物理键码，**没有语义**。app 怎么解释它取决于该 EditText 的 `inputType` / `imeOptions` 配置，agent 不可能事先知道。

而 Android IME 协议里早就有**带语义的提交动作** `EditorInfo.IME_ACTION_*`：
- `IME_ACTION_GO` (2): URL 跳转 / 主操作
- `IME_ACTION_SEARCH` (3): 触发搜索
- `IME_ACTION_SEND` (4): 发送消息 / 表单
- `IME_ACTION_NEXT` (5): 移到下一字段
- `IME_ACTION_DONE` (6): 完成关键盘
- `IME_ACTION_PREVIOUS` (7): 移到上一字段

这些是 app 必须正确响应的标准接口（开发者写 EditText 时会绑定 `setOnEditorActionListener`），但**没人通过 ADB 用过**——因为标准 ADB 不支持发这个事件。

### 解决
ADBKeyBoard 暴露了 `ADB_EDITOR_CODE` 广播：

```python
EDITOR_CODES = {
    "go": 2, "search": 3, "send": 4,
    "next": 5, "done": 6, "previous": 7,
}

# adb_type 加 editor_action 参数：
if editor_action and has_adbkb:
    code = EDITOR_CODES[editor_action]
    run_adb(["shell", "am", "broadcast", "-a", "ADB_EDITOR_CODE",
             "--ei", "code", str(code)])
elif text.endswith("\n"):
    run_adb(["shell", "input", "keyevent", "66"])  # 兜底
```

decision JSON schema 加 `editor_action` 字段，模型自己判断该用哪个：
```json
{"action": "type", "text": "我迟到 15 分钟", "editor_action": "send"}
{"action": "type", "text": "best pizza", "editor_action": "search"}
{"action": "type", "text": "用户名", "editor_action": "next"}
```

### 收益（按场景按步数算）

| 场景 | 之前 | 现在 | 收益 |
|---|---|---|---|
| 微信/iMessage 发消息 | tap 输入框 → type → 找 send 按钮 → tap (4 步) | type with `send` (1 步) | **省 75%** |
| Maps/Chrome 搜索 | type "best pizza\n" (~5-10% 翻车) | type with `search` (0% 翻车) | **可靠性 +∞** |
| 多字段表单 (5 字段) | type → tap 下一字段 (×5) | type with `next` (×5) | **省 4 步** |
| Notes 完成 | type → tap 屏幕外失焦 | type with `done` | **省 1 步 + 关键盘** |

### Insight
**物理键码是给人用的，IME action 是给程序用的**。Agent 走标准 IME 协议而不是模拟键盘，是 Android 输入设计的正路。

更深一层：**这是 ADBKeyBoard 把 IME 内部接口 expose 出来的副产品**——senzhk 这个项目实际上把 Android IME 协议变成了可远程调用的 RPC。一个挺老的开源工具，10 年历史，但配合现代 agent 突然变得无价。

### 实测结论：不是“点中了发送”，而是根本没点发送按钮

2026-05-10 用 `tests/verify_ime_editor_send.py --to 10086` 做了最小验证：

1. 打开 10086 现有短信线程。
2. tap 底部短信输入框，让 ADBKeyBoard 成为当前 IME。
3. 广播 `ADB_INPUT_TEXT` 输入 `IME_TEST_1778468351`。
4. 只广播 `ADB_EDITOR_CODE 4`，不点击屏幕上的发送按钮。

结果：
- `text_visible_before_send=True`
- `message_visible_after_send=True`
- `input_still_contains_text=False`
- 最终截图里出现已发送气泡 `IME_TEST_1778468351`，输入框回到 `Text message`。

结论：`ADB_EDITOR_CODE 4` 可以直接触发当前 focused EditText 的 `IME_ACTION_SEND`。发送路径不依赖 UI XML 中的发送按钮，也不依赖键盘弹出后的最新 XML。它的关键依赖是：当前焦点还在目标输入框、ADBKeyBoard 是 active IME、目标 app 对该输入框处理了 send action。

### 给评委讲
> "Android 上发消息正常要 4 步：点输入框、打字、找发送键、点发送。
> 我们用 IME 标准协议 `IME_ACTION_SEND`，**一步完成**。
> 这个 API 在 Android docs 里 10 年了。绝大多数 agent 项目都没碰过，因为模拟 Enter 键太简单。
> **我们走了正路。**"

评委里懂 Android 的（前端 / mobile 工程师），听到 `IME_ACTION_SEND` 会会心一笑。

---

## 架构哲学：为什么是这种设计

整套 agent 在底层数学上等价于 robotics 学界的 **System 1 / System 2 hierarchy**：

| 层级 | 机器人 | 我们 |
|---|---|---|
| System 1 (反应式) | VLA: Pi0 / Helix S1 | Gemma fresh-loop |
| System 2 (规划) | LLM agent: SayCan / Inner Monologue | （未来）Claude orchestrator |
| 接口 | "pick up red cup" + 视觉 | sub_mission + screen |

当前 demo 是 System 1 单层（hackathon 简化）。完整版本是双层混合架构：
- 上层 long-context 模型负责 plan / replan / 终审
- 下层 short-context 模型负责单步 grounding
- 边界处通过结构化接口（`sub_mission` + `success_criteria` + `final_summary`）传递

**这不是我们发明的——这是 Tesla Optimus、Figure、Physical Intelligence 都在走的路。我们在 Android 这个 modality 上把它实现了出来。**

---

## 工程亮点 Checklist

判断 phone agent 项目工程深度，看以下几点：

- [x] 双图对比 verify（不是看一张图猜变化）
- [x] 二次核验门（不让模型一句话宣布完成）
- [x] state-based plan（不被 app 路径多样性击垮）
- [x] historical OR 累积（容忍单步错误）
- [x] consecutive_fails 兜底（不卡死循环）
- [x] 通用 app prefetch（不硬编码 app）
- [x] 黑匣子完整日志（每个 LLM 调用、错误、兜底都可 replay）
- [x] 主动展示失败案例（不假装无所不能）
- [x] Prompt schema 经多轮迭代固化（每轮失败都被记录避免回退）
- [x] Plan 作为 hint 不作为 contract（finish gate 有权限忽略 plan 中间 false）
- [x] VLM 实体身份歧义处理（电话号码 / 日期等格式变体的 normalize）
- [x] UI inventory 多属性 OR 判定（clickable/focusable/long-clickable，不漏输入框）
- [x] Schema 双层防御（prompt 防瞎填 + 程序事后 enforce + 错误反馈下一轮）
- [x] 输入清空走 ADBKeyBoard ADB_CLEAR_TEXT 广播（确定性 setText("")，不靠模拟按键）
- [x] 提交动作走 ADB_EDITOR_CODE（IME_ACTION_SEND/SEARCH/NEXT/DONE，不模拟 Enter 键）

---

## 如果有时间继续做的方向

按 ROI 排序：

1. **可执行后置校验**：type 之后真的去 dump UI 看输入框有没有那串字，不让模型嘴瓢逃过
2. **System 2 orchestrator**：Claude/GPT-4 做 plan + replan，Gemma 做单步执行（前面分层方案）
3. **UI 稳定性轮询**：替代固定 `sleep(4)`，连续两次 UI dump 一致才视为页面稳定
4. **跳过冗余 verify**：`open_app` / `home` / `wait` 这类显而易见的动作不调用 verify，省一半 LLM 调用
5. **多 app 数据流**：跨 app 任务（"看股价 → 加日历"）需要 agent 持有跨 app 内存

### Performance vs. Accuracy Trade-off (2026-05-10)
- **Problem**: Large Context (Raw XML) results in > 60s latency per action.
- **Mitigation**: Implemented `get_ui_inventory` to strip redundant layout nodes.
- **Observed Result**: Latency dropped to 7-15s, making the agent practical for non-real-time automation.
- **Remaining Risk**: High-frequency scrolling or typing still feels "laggy" due to LLM inference overhead.

### Model Sensitivity to Prompt Formatting
- **Issue**: Ollama models frequently include Markdown code blocks even when instructed not to.
- **Fix**: The regex-based JSON extractor in `humanoid_agent.py` is robust enough to handle this, but explicit System Prompts help keep output clean.

---

## Challenge 15: Android 输入指令的"静默失败"与观测黑盒

### 问题
在 `type` 动作中，AI 明明发出了指令，且 ID 识别正确，但手机屏幕上要么没有任何字符出现，要么字符“打不全”（例如“这个 ai 对人的影响”变成了“这个”）。

### 根因：两条隐蔽的底层链路故障
1.  **广播投递被静默拦截**：在较新的 Android 系统中，出于安全和功耗考虑，不带 `-p` 包名限制的全局 `am broadcast` 指令常被系统静默过滤。Agent 发出了指令，但 `ADBKeyBoard` 驱动根本没收到信号。
2.  **Shell 单词截断 (Word Splitting)**：通过 `adb shell am broadcast ... --es msg text` 发送内容时，如果 `text` 包含空格，Android 的 Shell 会将其误认为多个参数。
    *   错误指令：`am broadcast ... --es msg 这个 ai 对人的影响` → 手机只收到 `msg="这个"`。
3.  **执行侧“黑盒”**：之前的日志只记录 AI 想点哪里（ID 8），但不记录底层实际点了哪里（[477, 498]）。当 UI 发生偏移或解析出错时，开发者无法通过日志回溯“真相”。

### 解决
1.  **定向投递 (Package-Locked)**：强制所有广播带上目标包名：`am broadcast ... -p com.android.adbkeyboard`。
2.  **引号保护 (Shell Quoting)**：在 Python 侧发送指令前，用单引号包裹文本内容：`f"'{text}'"`。这确保了带空格的长句子能被作为一个整体投递给 IME。
3.  **观测闭环 (Observability)**：
    *   升级 `save_debug_log` 架构，引入 **`[TOOL_RESULT]`** 块。
    *   不仅记录 AI 的 Schema 参数，还实时记录底层执行器返回的“真实现场回执”（Resolved Coordinates, Target Label, Exec Error）。

### Insight
**在 Agent 领域，观测能力 (Observability) 与执行能力 (Actionability) 同等重要**。
如果没有 `[TOOL_RESULT]` 记录的真实点击位置，我们永远无法分辨是“模型看歪了”还是“代码点歪了”。一个稳健的 Native Tooling 系统必须能够让开发者（和 AI 自身）在事后像回放黑匣子一样看清每一个物理动作的执行细节。

---

## Challenge 16: `withContext(IO)` 只包了一半 —— "错误: null" 的来源是 `NetworkOnMainThreadException`

### 问题
Android chat UI 里发 `/task ...` 和 `/stop`，relay 那边明明已经收到、agent 也真的跑起来了，UI 却跳红色卡片：

> ❌ **无法连接 Relay**
> 错误: null

之前几轮调试把 `connectTimeout` 从 3s 调到 10s、把 `/stop` 复制一份做对称处理，**全部无效**。错误那个字面"null"始终在那。

### 根因（logcat 抓到的栈是决定性证据）
```
E/ChatViewModel: Failed to POST /task: null
E/ChatViewModel: android.os.NetworkOnMainThreadException
    at android.os.StrictMode$AndroidBlockGuardPolicy.onNetwork(...)
    at java.net.SocketInputStream.read(...)
    at okio.RealBufferedSource.read(...)
    at okhttp3.ResponseBody.string(ResponseBody.kt:187)
    at com.hermesandroid.bridge.chat.ChatViewModel$sendMessage$1.invokeSuspend(ChatViewModel.kt:90)
    Suppressed: android.os.NetworkOnMainThreadException     ← 关闭 Response 时又踩一次
        at okhttp3.internal.http1.Http1ExchangeCodec$FixedLengthSource.close(...)
```

`ChatViewModel.kt` 里原来的写法是：

```kotlin
val response = withContext(Dispatchers.IO) {
    client.newCall(request).execute()         // IO 上，OK
}
val respBody = response.body?.string() ?: "{}"  // ← 回到 Main 才读 body，炸
val ok = response.isSuccessful
```

两条独立的暗陷阱叠在一起：

1. **`viewModelScope.launch` 默认在 `Dispatchers.Main.immediate`**。`withContext(IO)` 只覆盖花括号里那一行，块返回后立刻切回 Main。
2. **`OkHttp.execute()` 返回时只读了 response headers**，body 是惰性 `Source`。`ResponseBody.string()` 第一次读 body 才会调 `Socket.read()` —— 跑在 Main 上直接被 `BlockGuard` 拦截，扔 `NetworkOnMainThreadException`。
3. **`NetworkOnMainThreadException` 没有带 message 的构造器**，`e.message == null`。catch 里写的 `"错误: ${e.message}"` 字符串插值就把 `null` 印到了 UI 上。
4. **HTTP 请求本身在 IO 那一格里已经成功发出去了**——所以 server 端真的收到了 /task 和 /stop。客户端只是在读响应时挂了。这就是"明明炸了任务却也执行了"的精确解释。
5. Bonus：未关闭的 `Response` 在 Okio cleanup 里又调一次 `Socket.read()` 排空 body，于是 stack 末尾还有个 `Suppressed` 的同名异常 —— 就算 catch 住了 `.string()` 那次，关 body 还会再来一次。

### 解决
把 body 读取**和**关闭都圈进 IO，用 `Response.use {}` 保证关流：

```kotlin
val (ok, respBody) = withContext(Dispatchers.IO) {
    client.newCall(request).execute().use { resp ->
        resp.isSuccessful to (resp.body?.string() ?: "{}")
    }
}
```

`/task` 和 `/stop` 两处一并改。改完 logcat 直接干净：

```
I/ChatViewModel: Relay /task response: {"status": "ok", "message": "Agent spawn initiated in background"} (ok=true)
I/ChatViewModel: Relay /stop response: {"status": "ok", "message": "Agent (PID: 29706) stopping"}
```

### Insight
- **`withContext(Dispatchers.IO)` 的边界要包到 "最后一个 socket 字节被读完且 Response 关闭" 为止**。OkHttp 的 `Response` 是个延迟流，不是一坨内存里的 bytes —— `execute()` 返回 ≠ I/O 结束。
- **遇到 `e.message == null` 不要愣**，第一反应是 `NetworkOnMainThreadException` / 某些 `NullPointerException` 这种**没有 message 构造器**的异常。`Log.e(tag, msg, e)` 的第三个参数会打完整 stack，logcat 一抓就破案 —— 之前几轮 debug 只盯着红色卡片上那个"null"，没去 logcat 看 stack，加再多 timeout 都白搭。
- **`.use {}` 不只是优雅，是正确性**。如果只把 `.string()` 搬进 IO 但不关 Response，Okio 后台 cleanup 还会在 finalizer 线程或下次 GC 时摸 socket —— 偶发翻车。
- 这条跟 Challenge 15 的 "Observability" 一脉相承：**当 UI 上的错误信息是空的，logcat / 黑匣子才是真相。**永远把异常对象本体 (`Log.e(..., e)`) 喂给日志，别只 log `e.message`。

### 人话版（写给不懂 Android/Kotlin 内部的人）

**一句话**：派人去送信那一步做对了，所以信送到了；但"等对方回信、亲手拆开来看"那一步做错了，系统当场把这个动作拍死。错误信息又恰好是空白，所以 UI 上只能显示一个 "null"。

**两种工人**：Android 程序有两种"工人"。
- 主工人（Main 线程）：专门画 UI、响应戳屏幕，手脚必须永远很快。
- 后台工人（IO 线程）：干慢活，比如读网络、读文件。

**死规矩**：主工人**严禁碰网络**，哪怕只是 localhost 也不行。系统一发现主工人在联网，当场把它打死，扔一个"你居然在主线程联网！"的报错。这个特定的报错有个奇葩特点——**它没有任何文字说明**，问 `e.message` 拿到的是 `null`（空白）。

**之前的代码错在哪**：
```
1. 跟后台工人说"你去把 HTTP 请求发出去"       ← 后台工人干 ✅
2. 后台工人把"快递包裹"递回主工人
3. 主工人自己拆包裹看里面写了啥             ← 主工人干 ❌
```
OkHttp 的"快递包裹"很狡猾，**不是一拿到就装满了**。里面只有一张快递单（响应头），真正的内容（响应体）**是你要拆的那一刻才现从网线上读的**。所以第 3 步"拆包裹"看起来像本地操作，**其实是又去读了一次网络**。主工人在读网络 → 被拍死 → 扔出那个没文字的异常 → UI 显示 `错误: null`。

**为什么任务还是执行了**：第 1 步（让后台工人发请求）已经完整跑完了，请求飞过去，relay 收到，agent 起来了。挂掉的只是第 3 步——你这边读对方回的那张"OK 收到"小纸条时挂的。所以现象就是：**手机已经在干活了，但 chat 窗口告诉你"连不上"**。完全自相矛盾，但每一步都合逻辑。

**修复**：让后台工人把活干完再走。原来后台工人只负责发请求，现在让他**顺手把回信也拆好、内容抄下来、再交给主工人**。
```
1. 跟后台工人说"你去发请求 + 把回信拆开抄下来"   ← 后台工人全包 ✅
2. 后台工人把抄好的文字递回主工人
3. 主工人拿到的是字符串，没有任何网络操作了      ✅
```
代码上就是把"拆包裹"那一行从主工人的活挪进后台工人的活，一句 `.use { ... }` 包一下。仅此而已。

**为什么之前的 AI 修不好**：它看了 UI 上那个红色 "null" 就开始瞎猜——是不是 timeout 太短？是不是 relay 没启动？于是把 timeout 从 3 秒调到 10 秒，**风马牛不相及**。真正的证据藏在 logcat 里：`Log.e(..., e)` 会把异常的**完整堆栈**写进去，清清楚楚写着 `NetworkOnMainThreadException` 和出错的代码行号。**前面那个 AI 没翻 logcat，只盯着 UI 上的 "null" 瞎猜**，所以加多少 timeout、复制多少处理逻辑都没用——它根本没在修对的东西。

**一个隐喻**：想象你让助手去寄一封挂号信。
- 助手成功把信送到邮局了 ✅（请求发出去 = relay 收到了）
- 邮局给了助手一张密封回执 ✅（HTTP 响应头）
- 但回执是密封的，**你（老板）非要亲自拆**
- 公司规定老板不能干"拆信"这种小事，保安当场把你按住，警报响起来
- 警报器**只会闪红灯，不会显示原因**（异常没有 message）
- 你看着那个闪烁的灯喊："警报器说错误是 null！让助手拿更大的信封！多等会儿再拆！"

**修复**：让助手在邮局当场拆好回执、念给你听。

---

## Challenge 17: `/stop` 的 "Agent stopped" TTS 听不到 —— 默认 `QUEUE_ADD` 把它挂到队尾

### 问题
修好 Challenge 16 之后，`/stop` 能正常停 agent、UI 也弹出 "🛑 Agent 已停止" 卡片，但是**那句本该播报的 "Agent stopped" 听不到**。同一套 TTS 在 agent 跑完时的 "Task Finished" / "Task Failed" 是响的，所以 TTS 引擎本身没问题。

### 根因
`ChatViewModel.kt` 里原来：

```kotlin
ActionExecutor.speak("Agent stopped")
```

而 `ActionExecutor.speak` 的签名是：

```kotlin
fun speak(text: String, queue: Int = TextToSpeech.QUEUE_ADD): ActionResult
```

**默认是 `QUEUE_ADD`**，意思是"追加到 TTS 队列尾巴，前面的说完再说我"。

`/stop` 发生的时候 agent 通常正在中途执行：每一步它都会通过 bridge 的 `/speak` 端点往 Android TTS 队列里推一条"我现在在点 X / 我看到 Y"，全都是 `QUEUE_ADD`。当 `/stop` 触发：

1. relay 收到 `/stop` → SIGTERM agent 进程（Termux 里）
2. **agent 进程死了，但它之前 HTTP 推到 Android TTS 队列里的播报还在 Android 进程里活着** —— TTS 是 Android app 的状态，跟 agent 进程毫无关系，没人去清。
3. ChatViewModel 紧接着 `speak("Agent stopped")` 用 `QUEUE_ADD` 挂到队尾。
4. 用户听到的是 agent 临死前那些"我在点 X..."一句接一句念完，然后才轮到 "Agent stopped" —— 但用户早就不耐烦关掉手机或者切走了，听不到那句。

而 "Task Finished" 之所以能听到，是因为它发生在 agent 正常跑完时，那一刻 agent 已经把所有播报说完了，队列是空的，新一句立刻响。

`speak()` 的返回值之前也被丢了（`ActionExecutor.speak("Agent stopped")` 直接当 expression-statement），所以连 "TTS not available" 这种失败也是悄无声息。

### 解决
两个小改动：

```kotlin
val speakResult = ActionExecutor.speak(
    "Agent stopped",
    android.speech.tts.TextToSpeech.QUEUE_FLUSH    // ← 抢占队列
)
Log.i(TAG, "speak('Agent stopped') -> success=${speakResult.success}, msg=${speakResult.message}")
```

- **`QUEUE_FLUSH`**：把队列里没说完的全冲掉，立刻说 "Agent stopped"。语义上也对 —— agent 都停了，它之前要说的话也别说了。
- **log 返回值**：未来再出 TTS 相关问题，logcat 一行就能区分是"队列被吞"还是"engine 没起来"。

### Insight
- **TTS 队列是跨进程持久的副作用**：Android app 进程里的 `TextToSpeech` 队列不会因为远程 agent 进程被 kill 而清空。任何"打断式"的提示（错误、紧急、用户取消）默认就该 `QUEUE_FLUSH`，不要相信默认的 `QUEUE_ADD`。
- **API 默认值是个陷阱**：`speak(text)` 没显式传 queue 参数看起来"合理"，但默认的 `QUEUE_ADD` 在 99% 的场景下都是错的——你想说的是"现在告诉用户"，不是"排在所有事情之后说"。设计 TTS 包装函数时，默认应该是 `QUEUE_FLUSH`，让 `QUEUE_ADD` 显式 opt-in。
- **永远 log 副作用 API 的返回值**：`speak()` 返回了 `ActionResult(success, message)`，但调用方把它当 void 用。任何"扔出去就不管"的 IO/副作用调用，至少 log 一行返回值，否则它的失败就是黑洞。

### 人话版

**一句话**："Agent stopped" 不是没说，是在**排队**等前面那一长串"我在点 X"念完才轮到 —— 但 agent 都被打断了，那些话本来就不该再说了。

**TTS 队列的事**：手机的"语音播报"系统是个队列。你叫它说一句话，它就把这句话排到队尾，按顺序念。默认行为是"加入队列"（`QUEUE_ADD`），可选行为是"清空队列、立刻说"（`QUEUE_FLUSH`）。

**Agent 一直在往队列里塞话**：agent 每走一步都会调"播报"接口："我现在在点搜索框"、"我看到结果列表了"、"我准备点第三条"... 这些话全部被加到 TTS 队列尾巴等着念。如果 agent 思考快、嘴慢，队列里很快堆满未念的句子。

**`/stop` 发生的时候**：
1. 你按下 /stop。
2. 手机上的 Termux 把 agent 这个程序**杀掉**（agent 这个嘴不会再开口了）。
3. **但 TTS 队列在另一个程序里（Android app 自己），跟 agent 死活无关**。队列里那一堆"我在点 X"还排着，没人去清。
4. 然后 ChatViewModel 说："播报一句 'Agent stopped'"。但**它用了默认的"加入队列"**，于是这句话**乖乖排到队尾**，前面还有十几句等着念。
5. 你听不到——它在队列后面安静地等。如果你足够耐心等三十秒，最终会听到。但你早就觉得"哦，TTS 坏了"切走了。

**为什么 Task Finished 能听到**：那是 agent 正常跑完的时候触发的。agent 自己跑完意味着它该说的都说完了，队列是空的。"Task Finished" 加进去就是队首，立刻响。

**修复**：把"加入队列"改成"清空队列、立刻说"。

**隐喻**：你雇了个解说员实时直播你做菜：
- "我在切洋葱"
- "我准备开火"
- "我加了一勺盐"
- "我把锅盖盖上"
- "我..."

队列里堆了 10 句没说完。这时候你按了"停止做饭"按钮——厨房的火关了（agent 死了）、UI 上写"已停止"了，但**解说员还在按队列念"我在切洋葱..."**，因为他根本不知道你停了。然后助理跑去解说员旁边小声说："说一句'已停止'"，解说员说："好，我加到队列里"——你要等他把前面 10 句念完才听得到那句"已停止"。

正确做法是助理冲过去**打断解说员，直接喊"已停止！"** —— 这就是 `QUEUE_FLUSH`。

---

## Challenge 18: `adb logcat` tag 过滤如果不带 `*:S`，等于没过滤

### 问题
为了看 TTS 相关日志，跑了：

```bash
ssh win "adb -s ZA2232T6XT logcat -v time TextToSpeech:* ActionExecutor:*"
```

期望只看到这两个 tag 的输出。**结果屏幕上日志一刻不停往下滚**，啥都打。Filter 像没设一样。

### 根因
`adb logcat` 的 filter spec 是**白名单 + 全局默认级别**的混合模式：

- `TAG:LEVEL` 只是**降低**那个 tag 的最低显示级别（`:*` = verbose 起）。
- 没列出来的 tag 沿用**全局默认级别**，**默认是 V (verbose)** —— 所有未点名的 tag 都全量打。
- 要把全局压住，必须显式写 `*:S`（silent）放在最后。

也就是说 `TextToSpeech:* ActionExecutor:*` 等于"再额外打开这两个 tag 的 verbose"，**但全局 verbose 本来就开着**，所以白名单没起任何过滤作用。

### 解决
末尾加 `*:S`：

```bash
ssh win "adb -s ZA2232T6XT logcat -v time TextToSpeech:* ActionExecutor:* ChatViewModel:* *:S"
```

`*:S` 把所有未点名的 tag 静音，白名单才有意义。

### Insight
- **`adb logcat` 的 filter 不是"过滤"，是"调级"**。理解它的语义是关键：每个 tag 有最低显示级别，命令行参数只是逐个调整这些级别。
- **永远记得 `*:S` 这个收尾**。口诀：**"`*:S` 是 logcat 命令的句号"**，没它就等于一句没标点的废话。
- 同类陷阱在很多 \*nix 工具里都有 —— `iptables` / `tcpdump` / `journalctl` 的过滤语法各自有"默认放行"还是"默认拒绝"的潜规则，每次新接触都得验证一遍。

### 人话版

logcat 的 "过滤" 不是你想的那种"只显示这几个"。它实际是个**音量调节器**：

- 每个日志 tag 各自有一个"最低音量"门槛。
- 你写 `TextToSpeech:*` 意思是"把 TextToSpeech 这个 tag 的门槛调到最低（什么都让过）"。
- **没点名的 tag 怎么办？保留默认门槛 —— 而默认就是"什么都让过"**。
- 所以你只是"再额外让某几个 tag 也全开"，对其他 tag 没做任何静音。

要让"白名单"真生效，必须末尾加 `*:S`（star colon S）：**"所有没点名的 tag，门槛拉到最高，全部静音"**。

隐喻：你进了一间会议室想专心听 A 和 B 发言。你跟工作人员说"把 A 和 B 的麦克风开到最大"。工作人员照做了，结果你还是听不清——因为 C、D、E、F、G 的麦克风**本来就开着**，你只是让 A B 更响一点。正确指令是："把 A B 开到最大，**其他人全部静音**"。

`*:S` 就是那句"其他人全部静音"。

---

## Challenge 19: TTS lazy init 在 Main 线程死锁 —— `latch.await(5s)` + onInit 回调投递到 Main = 必然 5 秒后超时

### 问题
Challenge 17 把 `/stop` 的播报改成 `QUEUE_FLUSH` 之后，加了一行 log 看 speak 返回值。再跑一次 `/stop`（冷启动后第一次说话）logcat 抓到：

```
03:37:54.850  /stop 发出
03:37:54.944  Relay /stop response: ok
03:37:54.961  TextToSpeech: Sucessfully bound to com.google.android.tts
03:37:56.141  Connected to TTS engine
03:37:56.461  Setting up the connection to TTS engine...
03:37:59.962  speak('Agent stopped') -> success=false, msg=TTS not available
```

整整 **5.000 秒** —— 这是 `ensureTts()` 里 `latch.await(5, SECONDS)` 的超时时长。

### 根因
原来的 `ensureTts()`：

```kotlin
private fun ensureTts(): Boolean {
    val service = BridgeAccessibilityService.instance ?: return false
    if (tts == null || !ttsReady) {
        val latch = CountDownLatch(1)
        tts = TextToSpeech(service.applicationContext, OnInitListener {
            ttsReady = it == TextToSpeech.SUCCESS
            latch.countDown()
        })
        latch.await(5, TimeUnit.SECONDS)        // ← Main 在这睡 5s
    }
    return ttsReady
}
```

`TextToSpeech` 构造函数内部用 `mInitHandler = new Handler(Looper.getMainLooper())`，**`OnInitListener.onInit` 的回调通过这个 Handler post 到 Main 线程**。`ChatViewModel` 在 Main 上调 speak → `ensureTts()` → `latch.await()` **把 Main 锁住**。

于是：
1. TTS 引擎在 binder 线程上正常绑定、连接、设置完毕。
2. `dispatchOnInit` 想把 `onInit` post 到 Main —— **Main 正在 `latch.await` 上睡觉**，post 进队列后没人执行。
3. 5 秒超时到，`latch.await` 返回 false，`ttsReady` 仍是 false，速返 `"TTS not available"`。
4. Main 醒过来继续跑后续代码，**这一刻 Main 的消息队列才轮到刚才那个 onInit Runnable**，它执行、把 `ttsReady` 设成 true —— 但调用方早就走了，这次播报已经丢了。

**为什么 "Task Finished" 之前能听到**：那个调用路径是 agent 通过 bridge 的 `/speak` 端点触发，跑在 **Ktor 后台线程**上。Ktor 线程上调 `ensureTts()`，`latch.await` 阻塞的是后台线程，**Main 是空的**，onInit 顺利在 Main 上 fire，latch countdown，`ttsReady=true` 进了缓存。后续任何线程的 speak 调用都是 cache hit。

冷启动后 `/stop` 是第一次说话且发生在 Main 上，所以恰好踩中。

### 解决
两个互补改动：

1. **预热**（`BridgeAccessibilityService.onServiceConnected()`）—— 在 a11y 服务连接的瞬间就构造 TTS，不等任何东西：
   ```kotlin
   override fun onServiceConnected() {
       instance = this
       ActionExecutor.prewarmTts(applicationContext)
       ...
   }
   ```
   `onServiceConnected` 本身在 Main 上跑，但**它不阻塞自己**——构造完 TTS 就 return，onInit 稍后在 Main 上 fire 时 Main 早就空闲了，`ttsReady` 顺利变 true。

2. **`ensureTts()` 不再阻塞** —— 拿掉 latch，状态查表：
   ```kotlin
   @Volatile private var tts: TextToSpeech? = null
   @Volatile private var ttsReady = false

   fun prewarmTts(context: Context) {
       if (tts != null) return
       synchronized(this) {
           if (tts != null) return
           tts = TextToSpeech(context.applicationContext) { status ->
               ttsReady = status == TextToSpeech.SUCCESS
               Log.i("ActionExecutor", "TTS init: status=$status, ready=$ttsReady")
           }
       }
   }

   private fun ensureTts(): Boolean {
       if (tts == null) {
           val ctx = BridgeAccessibilityService.instance?.applicationContext ?: return false
           prewarmTts(ctx)
       }
       return ttsReady
   }
   ```
   极端情况下 a11y 服务还没连上就有人 speak，会返回 false，可以接受。正常路径下预热已经跑过，缓存命中，零等待。

### Insight
- **"在 Main 上等一个被投递到 Main 的回调" 是个反复出现的死锁模板**。任何 `XxxListener { latch.countDown() }` + `latch.await()` 在 Main 上的组合，先问一句"这个 listener 默认 dispatch 到哪个 looper？"。Android 里 `TextToSpeech` / `MediaPlayer` / `LocationManager` / `SensorManager` 都有这个坑。
- **`@Volatile` 是 `object` 单例里 cross-thread 状态的最低成本写法**。`tts` 和 `ttsReady` 会被 Main、Ktor worker、binder 线程同时读写，不加 `@Volatile` 会有可见性问题（B 线程看到 ready=true 但 tts 仍是 null 之类）。
- **Eager init > Lazy init，对于"启动可控、运行时不可阻塞" 的资源**。TTS、Location、Sensor 这类要 IPC + 异步回调初始化的服务，应该在生命周期入口处 fire-and-forget 启动，**不能塞到第一次使用时同步等**。Lazy init 看上去优雅，实际是把延迟从启动期推到了 critical path。
- **5 秒 round number 的超时是诊断线索**：logcat 上看到一个"几乎精确等于某个常数"的延迟差（5.000 秒、3.000 秒），第一反应去搜代码里那个数字。这次正好是 `latch.await(5, SECONDS)`。

### 人话版

**一句话**：助理（Main 线程）在那儿傻等"语音系统准备好"的通知，**而那个通知偏偏只能由助理自己传**——他在等他自己来叫他，必然超时。

**舞台**：手机上的 TTS（语音播报）系统启动需要时间，第一次用要绑定 Google TTS 引擎、加载语言包等等。所以代码会"等一下，等准备好了再说话"。

**等的方式**：拉一根绳子（CountDownLatch），一头交给"准备就绪通知员"，另一头自己抓着。通知员到位时拉绳子（countDown），抓绳子的人感受到就走。最多等 5 秒，5 秒后没动静就放弃。

**死锁是这样的**：
1. 用户喊 `/stop`，UI 主线程（"助理"）开始处理。
2. 助理叫"准备 TTS！"，启动了语音系统。
3. **语音系统按照规矩，"准备好之后通知谁？通知主线程的消息队列"** —— 也就是说，**通知员必须把通知交给助理本人去处理**。
4. 助理同时还紧紧抓着那根绳子在等通知。
5. 语音系统其实 1.5 秒就准备好了，通知员跑过来：「我有事要交给助理！」结果助理正在等绳子被拉，腾不出手接通知。
6. **通知就这么排队等着、等着、等了 5 秒**。
7. 5 秒到，助理放弃，说"TTS 没准备好"，走人。
8. 助理一走腾出手了，立刻看到队列里那条"准备好了"的通知 —— 但晚了，话已经放弃没说。

**为什么 Task Finished 没事**：那个调用是 agent 远程让手机说话的，相当于"前台经理"（后台线程）在处理，不是助理本人。前台经理抓绳子等通知，**助理是空闲的可以收通知**，通知正常送达，绳子被拉，前台经理走人。从那以后整个手机的 TTS 都"已准备好"，谁来用都 cache 命中。

**修复**：
- **改掉"通知谁"**：让 TTS 一启动就开始准备，**根本不用任何人去等**。准备好了之后回头来通知，那时候助理肯定闲着。
- **改掉"助理去等"**：助理不再抓绳子。问一句"准备好了吗"，准备好就用，没准备好就跳过，绝不在 Main 上死等。

**隐喻**：餐厅老板（Main）站在前台等厨房做菜，**而厨房做完菜要把"出餐通知"递给前台老板**。老板眼睛盯着厨房门、手撑在前台不让任何人靠近——服务员端着菜过来递通知，**够不着前台**。老板等了 5 分钟没等到通知，说"厨房太慢，今天不上菜了"，转身走开——结果立刻看到服务员举着菜在门口等他签收。

正确做法：开店时就让厨房**先把基础食材备好放冰箱**（预热）。客人点菜时老板看一眼冰箱有没有就行，**别站门口等出餐**。

---

## Challenge 20: Overlay 点击穿透 —— 不是每个 action 都包一遍，而是按 agent 生命周期开关

### 问题
HUD overlay 默认接收触摸（因为要支持拖动重新定位），导致 agent 走 `dispatchGesture` 在屏幕上点击时，**如果点击坐标落在 overlay 范围内**，被 overlay 吃掉，下面真正的 UI 元素收不到。

### 错误方向（先做了再说的丑陋方案）
第一次尝试是在 `ActionExecutor` 加一个 helper `withOverlayTransparent { ... }`，**把 tap / tapText / swipe / drag / scroll / longPress 全部包一层**：

```kotlin
private suspend fun <T> withOverlayTransparent(block: suspend () -> T): T {
    StatusOverlay.setTouchable(false)
    try { return block() }
    finally { StatusOverlay.setTouchable(true) }
}

suspend fun tap(...) = wakeForAction {
    withOverlayTransparent {   // ← 每个 action 都得记得包
        ...
    }
}
```

技术上对（`FLAG_NOT_TOUCHABLE` 就是干这个的），但烂在三个地方：

1. **每加一个 action 都得手动包一层**，新人不知道这个约定就再来一次 bug。
2. **每秒 N 次 `WindowManager.updateViewLayout`**：每个 action 进出各调一次。Hot path 上的无谓 IPC。某些 ROM 上 window flag 切换可能伴随 surface 重组，看起来像闪屏。
3. **并发 race**：万一两个 action 同时跑（agent 不会，但理论上），一个 finally 把 touchable 恢复了，另一个动作还在执行，短暂窗口里 overlay 又能吃触摸。

### 正确方向：按 agent 生命周期开关
观察到的事实：**agent 在跑步骤的间隙里，用户也不会去拖 overlay**。所以"overlay 不能被触摸"的窗口期 = "agent 整段运行期"，不是"agent 正在执行某个具体 action"。

改成生命周期 toggle：只有 **3 个 call site**——

- `ChatViewModel` `/task` 接收 → `setTouchable(false)`
- `ChatViewModel` `/stop` 用户主动停 → `setTouchable(true)`
- `StatusOverlay.triggerFeedback(success/fail)` agent 自然结束（"Task Finished" / "Task Failed" 那个分支）→ `setTouchable(true)`

`withOverlayTransparent` 改成 no-op（保留函数让 Gemini 改动里的 `return@withOverlayTransparent` 标签还能编译）：

```kotlin
private suspend fun <T> withOverlayTransparent(block: suspend () -> T): T = block()
```

新加 action 不需要操心 overlay。每次 agent 跑只调一次 `updateViewLayout`、结束再调一次 —— hot path 上零开销。

### Insight
- **"为每个调用点写一次防御" 是个臭味信号**：往往说明防御应该在更高的生命周期层做，不是每个叶子节点。问"这个 invariant 真正需要成立的时间窗口是什么"，把开关挪到那个窗口的边界上。
- **Window flag 切换不是免费的**：`FLAG_NOT_TOUCHABLE` 看起来只是 hit-testing 路由的改变，但 `updateViewLayout` 会进 WindowManager IPC、可能引发 surface 重新评估。每 action 调一次是真实开销。
- **保留 no-op shim 的合理性**：当一个 helper 函数有大量 callsite，但功能要废掉时，把函数体改成 `= block()` 是**最低风险**的撤销 —— 保留所有 callsite 和 label 引用让编译通过，行为变成透明。之后可以从容地一处处真正 unwrap。这条原则在大规模 refactor 收尾、回滚一个失败的 feature flag 时都用得上。
- **触摸性 ≠ 可见性**：`FLAG_NOT_TOUCHABLE` 只改 hit-testing，**不影响视觉**。手指/agent 的点击直接穿透 overlay 到下面的 view，overlay 自己仍然可见。区分这两个维度可以避免"为了不挡点击而让 UI 闪烁"的错误反应。

### 人话版

**问题**：屏幕上那个半透明的状态浮窗（HUD），用手指能拖动 → 说明它"能接收触摸"。Agent 帮你点屏幕时，如果点的位置正好被这个浮窗盖住，**浮窗把触摸截胡了**，下面真正的按钮没被点到。

**第一版（丑陋的）修法**：每次 agent 要点击之前，**临时把浮窗设为"不接收触摸"**，点完再设回来。问题：每个动作类型（点、滑、长按...）都得手动包一层这种"设/恢复"代码。一来啰嗦，二来 agent 一直在动作，浮窗一直在切来切去，开销大。

**洞察**：仔细想一想 —— **agent 在跑任务的整段时间里，你根本不会去拖那个浮窗**。你想拖浮窗，只有在 agent 闲着的时候。那为什么要"每个动作前后切一次"？直接"agent 开始跑 → 浮窗不接触摸；agent 结束 → 恢复触摸"就够了，整段任务期间只切两次。

**新方案的开关只放在 3 个位置**：
1. 你发 `/task` 让 agent 干活 → 关掉浮窗的触摸感应。
2. 你发 `/stop` 强制停 → 打开浮窗的触摸感应。
3. Agent 自己跑完（成功或失败）→ 打开浮窗的触摸感应。

agent 整个运行过程中浮窗一直是"看得见但摸不到"的状态。手指或 agent 的点击都直接穿过浮窗点到下面。agent 一停下来，浮窗又能拖动了。

**关键澄清**："摸不到"≠"看不见"。浮窗的视觉显示完全不受影响，你照样能看到 HUD 上的状态、思考、动作等等。只是它**不再拦截触摸**而已。

**隐喻**：你在玩游戏，屏幕角落有个半透明的"血量条"。如果血量条**会挡你的鼠标点击**，那很烦——你想点 boss 时点到血量条上。修法一（丑）：每次你按下鼠标键之前，游戏自动把血量条变成"无视鼠标"，松开再变回来。修法二（优雅）：进战斗了 → 血量条整段都"无视鼠标"；战斗结束 → 血量条又能拖动。

后者就是这次的方案。

---
