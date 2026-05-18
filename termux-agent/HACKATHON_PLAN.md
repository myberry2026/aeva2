# Hackathon Demo Plan

## 主题对齐：Gemma4 for Good

赛题两个维度，我们都正中靶心。

### 为什么必须是 Gemma4（不是 GPT-4o / Claude）

| Gemma4 特性 | 对 phone agent 的意义 |
|---|---|
| 🔒 本地运行 | 手机数据不出设备，是 phone agent 的伦理底线 |
| 💸 免费开源 | 不依赖订阅，全球低收入用户都能用 |
| 👁️ 多模态视觉 | 能看屏幕（云模型也行但需联网+付费） |
| 🔧 Google 出品 | Gemma 在自家 Android 上跑最顺 |
| 📅 新出 | 之前的 Gemma 跑不动 vision-heavy 任务，Gemma4 是临界点 |

→ **Slogan 候选**："The first phone agent you can actually trust on your phone—because it never leaves it."

### 为什么是 "for Good"——谁被 underserve 了

主流 phone agent (Apple Intelligence、ChatGPT app) 的隐性用户画像：
- 会用智能手机的中产
- 能看清屏幕的成年人
- 手指灵活、能精准点击
- 信任云服务、付得起订阅

**这外面就是 for Good 的舞台**：

| 受益群体 | 当前痛点 | 我们怎么帮 |
|---|---|---|
| 80+ 老年人 | UI 太复杂，学不会 | 一句话操作任何 app |
| 视障 / 低视力 | 看不清屏幕 | 语音输入 + 自动操作 |
| 帕金森 / 关节炎 / 中风后 | 手抖点不准 | 不需要精准触控 |
| 低识字率 (老人、儿童、移民) | 读不懂复杂界面 | 自然语言操作 |
| 隐私敏感人群 (家暴受害、活动家、医疗) | 不能让数据上云 | 本地 Gemma，零上云 |
| 低收入地区 | 付不起 cloud AI 订阅 | 永远免费 |

→ 我们的 agent **正好解决这六类人的核心痛点**——不是巧合，是 **本地+通用** 这两个架构选择带来的副产品。

---

## 核心定位

**通用性是护城河**。别人的 agent demo 都是单一场景（OpenAI 演 Mac、Anthropic 演浏览器、X 演 DoorDash），共同点都是"为某个特定任务做了适配"。

我们的卖点：**一套代码、零适配，通吃所有 Android app**。

技术基底：
- state-based plan（once-true-stays-true）
- 完整 status array verify（每步 checklist 全量重报）
- finish gate 二次核验（拒绝虚假成功）
- 通用 app prefetch（不绑死任何具体 app）

---

## 5 分钟 Demo 脚本（for Good 重组版）

```
[0:00-0:30] 钩子 — 问题陈述（情感）
"Smartphone 设计给了 90% 人。
 还有 10%（10 亿人）每天跟手机搏斗：
 - 80 岁的奶奶找不到微信对话
 - 视障朋友靠 TalkBack 用半天导航不出来
 - 帕金森患者试 5 次才点中按钮
 现有 AI 助手靠云、靠订阅、要新手机——
 他们一个都用不上。"

[0:30-1:30] 解决方案 — 我们是什么 + 为什么 Gemma4
"我们做了一个 phone agent，跑在 Gemma4 本地：
 ✓ 一句话操作任何 app
 ✓ 完全离线，数据不出设备
 ✓ 免费，永远免费
 ✓ 通用，不绑死任何 app
 这是 Gemma4 第一次让本地 phone agent 成为可能——
 之前的开源模型，要么不够聪明，要么跑不动视觉。"

[1:30-3:00] 现场 LIVE demo
 助老场景 + 多 app 串联（情感 + 技术深度）
 真手机投屏 + 终端 log 双屏

[3:00-4:00] 工程深度
 - 通用性原理（state-based criteria）
 - "我们不会骗用户"（finish gate 主动失败 demo）
 - Prompt schema v1→v9 演进图（评委看了知道我们 ship 过）

[4:00-4:30] 影响力 — 为什么是 for Good
"今天 demo 是 Maps 找披萨，但同样代码：
 - 帮老人打电话给医生
 - 帮视障用户在外卖 app 下单
 - 帮帕金森患者发微信
 一个 agent，10 亿人受益。"

[4:30-5:00] Gemma4 致谢 + 愿景
"这是为 phone 上的 every user 而做。
 Gemma4 的本地能力让它成为可能。
 谢谢 Google 让这个未来 ship 在我们手里。"
```

### 现场穿着 / 表演细节

- 别穿西装。讲"为弱势群体服务"穿正装违和，普通 T 恤更可信
- 讲奶奶场景时蹲下来跟手机平视，模拟"老人坐着用"视角
- 故意手抖一下假装帕金森再下指令——评委会笑也会记住
- 准备一句金句挂嘴边："This isn't AI for the next billion users. This is AI for the previous billion."

---

## 候选场景（9 个，按风险/视觉冲击力分级）

### 🟢 安全牌（demo 失败风险低）

#### S1. Maps 找店并获取信息
- 指令："在地图找方圆 1km 内评分 ≥4.5 的拉面店，告诉我地址和电话"
- 用 app: Google Maps
- 视觉：搜索 → 列表滚动 → 详情页 → 拨号
- 预计步数：5-7 步
- 已经在调，最稳定

#### S2. 天气 + 闹钟联动
- 指令："明天早上看天气，如果下雨就把 7 点闹钟提前到 6:30"
- 用 app: 天气 + 时钟
- 视觉：跨 app 切换、条件分支
- 预计步数：6-8 步

#### S3. 信息查询（Yelp/豆瓣）
- 指令："Yelp 找评分 ≥4.5、人均 50 刀以下的日料店"
- 用 app: Yelp 或大众点评
- 视觉：搜索 + 筛选 + 滚动
- 预计步数：5-6 步

### 🟡 出彩牌（视觉好但有风险）

#### S4. 「我马上迟到了」多 app 串联 ⭐ 推荐 LIVE
- 指令："给老板微信说我晚 15 分钟，给老婆短信说今晚回不来，把 7 点的健身房改到明天"
- 用 app: 微信 + 短信 + 日历
- 视觉：3 个 app 切换，节奏快
- 预计步数：10-12 步
- ⚠️ 注意：用小号微信，提前打开过

#### S5. 跨 app 数据流转
- 指令："看一下 Apple 股价，把当前价格加到我的笔记里，下周五提醒我看一次"
- 用 app: 股票 + Notes/Notion + 日历
- 视觉：信息从一个 app 流到另一个 app
- 预计步数：8-10 步

#### S6. 旅行场景模拟
- 指令："我刚到东京，告诉我现在天气、找一家拉面店评分 ≥4.5、导航过去、把地址存到笔记"
- 用 app: 天气 + Maps + Notes
- 视觉：多步骤连续，有故事性
- 预计步数：10-12 步
- ⚠️ 现场不在东京，要伪造定位或改时区

### 🔴 王炸牌（高风险高回报）

#### S7. 数字陪伴 / 助老场景 ⭐ 情感冲击最强
- 指令："看孙子最近发的照片，再给孙子打个电话"
- 用 app: 微信 + 拨号
- 故事：90 岁奶奶不会用智能手机，一句话搞定
- 视觉：开场情感钩子
- 建议：录 30 秒情景视频开场，再现场跑技术 demo

#### S8. 视障辅助
- 蒙住屏幕 / 关掉视觉反馈，纯语音指令完成"在 Maps 找咖啡店"
- 显示对比：「agent 看见的」vs「用户看不见的」
- 视觉：戏剧性极强
- ⚠️ 要做语音前端

#### S9. 残障无障碍
- 帕金森手抖患者输入难题
- 配真实手抖视频对比
- 一句话完成原本要点 30 次屏幕的操作

---

## Sizzle Reel 视频组成（60-90 秒）

每个场景剪 5-10 秒，5x 加速，配字幕：

| 时间 | 场景 | 字幕 |
|---|---|---|
| 0-8s | S1 Maps | "Find pizza, call them" |
| 8-15s | S4 多 app | "Tell boss I'm late, reschedule gym" |
| 15-22s | S2 天气+闹钟 | "Weather → adjust alarm" |
| 22-30s | S7 助老 | "Show grandma's photos" |
| 30-37s | S5 跨 app | "Stock price → note → calendar" |
| 37-44s | S3 Yelp | "Find ramen ≤$50" |
| 44-50s | 系统设置 | "Change ringtone" |
| 50-58s | S6 旅行 | "Just landed in Tokyo, set me up" |
| 58-60s | END frame | "One agent. Every app." |

---

## 主动失败 Demo（最关键的差异化）

构造一个 agent 会"诚实拒绝完成"的场景：

**指令**："在 Maps 找一家评分 ≥99 的店并打电话"（不存在）

**预期表现**：
- agent 搜索披萨
- 滚动找不到 ≥99 分的店
- 多次尝试后 mission_complete 永远 false
- consecutive_fails 触发兜底
- 最终 finish gate 否决任何 finish 尝试
- agent 主动报告："找不到符合条件的店，任务无法完成"

观众被打动的点：**别人的 demo 都演成功，我们演"我们的 agent 不会骗人"**——这是工程深度。

---

## 赛前准备清单（24 小时）

- [ ] 录 sizzle reel 8 个场景（4-6h，每个跑 3-5 遍取最好）
- [ ] 给每个场景做 plan cache（1-2h，避免现场 PLAN 拆错）
- [ ] 选 2 个 LIVE 备选场景（主选 + backup）（1h）
- [ ] 演练 LIVE 5 遍，时间卡死 5 分钟（2h）
- [ ] 准备「主动失败」demo（1h）
- [ ] 录 backup 视频（现场翻车就播）（1h）
- [ ] 准备 demo 用的小号微信、测试 app（30min）
- [ ] 投屏方案确认（手机 + 终端双屏）（30min）

---

## Demo 当天注意事项

1. **真手机投屏，别用模拟器**——评委一眼能看出来
2. **网络备好热点**——会场 WiFi 不靠谱
3. **手机插电、关通知**——避免 demo 中弹消息打断
4. **关闭无关 app**——避免后台占资源拖慢 ADB
5. **plan_cache 已加载验证**——避免冷启 PLAN
6. **终端字号调大**——评委要能看清 log
7. **失败有备案**：现场翻车就 "Let me show you the recorded version" 播视频

---

## 我能帮你做什么

| 需要 | 我能干 |
|---|---|
| 给 N 个场景写 plan cache | 你列任务 → 我出 plan 模板存进 `logs/plan_cache.json` |
| 设计「主动失败」demo | 构造场景 + 调 prompt 触发 finish gate 否决 |
| 写 60s reel 的解说字幕 | 给场景列表 → 出英文字幕脚本 |
| 调每个场景的稳定性 | 看 log 找失败模式针对性修 prompt |
| 帮录 demo 视频 | 给录制流程 + 后期剪辑要点 |

**下一步建议**：你列出最想 demo 的 5-6 个具体任务（要带 app 名 + 完整指令），我直接帮你出 plan cache，赛前每个跑通 3 遍就能录。
