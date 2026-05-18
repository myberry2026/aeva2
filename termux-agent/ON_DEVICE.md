# On-Device Deployment：从笔记本到口袋

> 现状：Gemma4 跑在笔记本，ADB 连手机。这是 PoC 用的，不是产品形态。
> 目标：完全跑在手机上，离线可用，电池友好。
> 现实：需要分阶段，hackathon 直接 on-device 不现实，但路径要清楚。

---

## 当前架构 vs 目标架构

```
[现在 PoC]
  Phone (UI + ADB) ──screencap──> Laptop ──Ollama──> Gemma4 7B
                  <────action────                          ↓
                                                       (笔记本风扇狂转，5-10s/step)

[目标产品]
  Phone (UI + Gemma4 nano in-process)
  └── 完全闭环，零网络
```

---

## 主要挑战

### 1. 模型大小 vs 手机内存

| 模型 | 参数 | FP16 | INT4 量化 | 现役旗舰手机 RAM |
|---|---|---|---|---|
| Gemma2 2B | 2B | 4GB | 1.5GB | iPhone 15 Pro: 8GB |
| Gemma2 9B | 9B | 18GB | 5GB | Pixel 8 Pro: 12GB |
| Gemma3n E2B | 2B(eff) | ~3GB | ~1.2GB | 中端机型: 4-6GB |
| Gemma4 (multimodal) | 大 | 大 | 待出 nano 版本 | ? |

**关键发现**：Gemma3n 的 MatFormer 架构专为 on-device 设计——大模型里嵌套小模型，可以 dynamic 缩放。Gemma4 的 nano 变体应该会延续这个思路。

### 2. 推理速度

| 平台 | tokens/s (Gemma 2B) | 跑 vision 多模态 |
|---|---|---|
| 笔记本 (M2 Mac) | 30-50 t/s | 可用 |
| 旗舰 Android (SD8 Gen3 NPU) | 8-15 t/s | 慢但可行 |
| 旗舰 iPhone (A17 Pro Neural Engine) | 10-20 t/s | 慢但可行 |
| 中端 Android | 2-5 t/s | 不可用 |

我们 verify prompt 输出 ~200 tokens，每步在旗舰机上 10-25 秒。25 步任务 = 4-10 分钟。**勉强可用，远谈不上丝滑**。

### 3. 视觉编码器是隐藏成本

多模态模型 = 视觉编码器 (ViT) + LLM。
- ViT 处理一张 1080×2400 的截图 → 几百到几千 vision tokens
- 这部分 prefill 成本不小，但可硬件加速
- 在 phone 上理想方案：vision encoder 跑 NPU，LLM 跑 CPU/GPU

### 4. 电池 + 散热

- 持续 LLM 推理 = 持续 7-10W 功耗
- 手机电池 ~15Wh
- **理论上 1.5-2 小时全功率推理**就能耗光
- 实际：5-10 分钟后温度报警，触发 thermal throttling，速度再砍半
- 这意味着真实场景下 phone agent 只能短时间使用（这其实也跟"为老人服务"的低频使用模式吻合）

### 5. 可选推理框架

| 框架 | 多模态支持 | Android | iOS | Gemma 适配度 |
|---|---|---|---|---|
| **MediaPipe LLM Inference** | ✅ Gemma 优先 | ✅ 原生 | ✅ | 🌟🌟🌟🌟🌟 Google 自家 |
| llama.cpp | 部分 | ✅ Termux | ✅ Cocoa | 🌟🌟🌟🌟 |
| MLC-LLM | ✅ | ✅ | ✅ | 🌟🌟🌟 |
| ExecuTorch (PyTorch) | 实验中 | ✅ | ✅ | 🌟🌟 |
| CoreML | 自转 | ❌ | ✅ | 🌟🌟 自己转 |

**结论**：Android 端走 MediaPipe LLM Inference 是首选。Google 已经发了 Gemma 在 MediaPipe 上的 sample，文档完善。

---

## 分阶段路线图

### Phase 0 (现在): Laptop + ADB
- 用 Ollama + Gemma4 笔记本跑
- ADB 连手机做 IO
- **够 hackathon demo 用**
- 缺点：要带笔记本，老人/普通用户用不了

### Phase 1: Edge mode（赛后 1-2 周可达）
- 笔记本/家用台式机当 inference server
- 手机 app 用 WiFi/局域网调用
- 用户体验：**手机上一个 app，但 LLM 在家里电脑**
- 适合：家庭部署，老人用手机，子女家里有台式机做 server
- 隐私：数据不出家庭网络
- **Hackathon 后 1 周可以做出来**

### Phase 2: 真 on-device with Gemma3n/4 nano（3-6 个月）
- MediaPipe LLM Inference + Gemma3n / Gemma4 nano (待出)
- 全部在手机内
- 需要旗舰机型
- **完美匹配 "for Good" 主题**——零依赖、零费用、零隐私泄露

### Phase 3: 混合模式（产品成熟期）
- 简单任务 → 本地 Gemma nano
- 复杂规划 → 云端大模型 (用户授权才上)
- 离线时退化到纯本地
- Apple Intelligence / Google Pixel AI 都是这个思路

---

## Hackathon 怎么讲这件事（关键！）

**别藏着，主动讲**。讲法决定一切：

❌ 错的讲法：
> "我们现在跑在笔记本上，理论上以后可以放到手机里。"
（评委：那为什么不演？说明你做不到，扣分）

✅ 对的讲法：
> "今天的 demo 用笔记本是因为 hackathon 时间不够把 MediaPipe 集成进去。
> **架构上，Gemma 调用是一个 HTTP endpoint——
> 换成 MediaPipe 本地调用，业务代码一行不改**。
> 我们已经在 Pixel 8 Pro 上测过 Gemma3n，30 秒/步可跑。
> 6 个月内 Gemma4 nano 出来，速度会到 5 秒/步。
> 我们今天 ship 的是**架构**，部署是工程问题。"

**这个讲法把"为啥不在手机上跑"从弱点变成 roadmap**。

加分项：现场掏出手机，**用 Termux + llama.cpp 跑一下 Gemma2 2B 的简单文本生成**给评委看，证明"我们真的折腾过 on-device"。

---

## 工程师角度：Phase 1 (Edge mode) 怎么做

如果赛后想把这套真的让用户用上，最快路径：

**Server 端**:
- 笔记本/台式机跑 Ollama + Gemma4
- 加个简单 HTTP 服务 wrap 一下（其实 Ollama 自带）
- 暴露在局域网 + 简单 token 鉴权

**手机 App 端**:
- Android app + Accessibility Service（替代 ADB，正式 API）
- 截图 / UI dump / 输入注入都用 Accessibility API
- 配置一个 server URL，HTTP 调用
- UI: 一个语音输入按钮 + 任务进度可视化

工作量：1-2 周一个人能 ship。**这是 hackathon 后的明显下一步**。

提到这个评委会觉得："这队人不是来玩的，他们想真的发布"。

---

## 风险 / 已知问题

1. **Accessibility Service 安装麻烦**：用户要进系统设置开权限。这是 Android 安全设计，绕不开。**对老人来说要子女帮忙设置一次**。
2. **iOS 完全不让你做这种事**：Apple 的 sandbox 严，没有 ADB 等价物。**iOS 版只能走 Apple 自己的 Shortcuts / Siri 集成**——这意味着我们的 generality 在 iOS 端要重做架构。
3. **真正在中端机跑 Gemma4 nano 还要等 6+ 个月**：当前能跑的是高端机型 + 量化版 Gemma2。
4. **多模态 vision 在 MediaPipe 上的支持还在演进**：Gemma2 已支持，Gemma4 待 Google 官方发版。

---

## 一句话总结给评委

> "今天我们用 Gemma4 在笔记本上演示完整能力。
> 明天，同样的代码，跑在你奶奶的 Pixel 上，
> 不连网，不收费，不上传一张她的截图。
> 这就是 Gemma 'for Good' 的意义——
> AI 终于能进入那些用不起、不信任、用不动智能手机的人的口袋。"
