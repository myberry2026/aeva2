# 测试案例记录 / Test Cases (CASES.md)

| 日期 | 任务目标 (Goal) | 最终状态 | 模型 | 关键笔记 |
|---|---|---|---|---|
| 2026-05-10 | 地图搜 'best pizza in SF' 并点 Call 后返回主页 | ✅ Success | gemma4:26b | 解决了“西西弗斯循环”，引入了状态审计机制。 |
| 2026-05-10 | 浏览器搜 'nvidia股票' | ✅ Success | gemma4:26b | 验证了 UI 元素嗅觉增强和坐标点击。 |
| 2026-05-10 | 设置明天 08:00 的闹钟并返回桌面 | ✅ Success | gemma4:26b | 验证了 `id: null` 的防御性报错与自我纠错。 |
| 2026-05-10 | 地图搜 Starbucks 记下地址并短信发给第一个人 | ✅ Success | gemma4:26b | 顶级跨应用任务。克服了登录弹窗、空联系人列表（改为新建聊天）等复杂障碍。 |
| 2026-05-10 | 通讯录新建 'Test Agent' (18888888888) 并保存 | ✅ Success | gemma4:26b | 克服了 Android 电话号码自动格式化造成的视觉干扰。 |
| 2026-05-10 | 时钟 App 点击 'Timer' 标签并返回桌面 | ✅ Success | gemma4:e4b | 验证了新远程模型 Gemma 4 e4b 的基础链路。 |
| 2026-05-10 | 浏览器算 '2026-1998' 并短信发结果给 10086 | ❌ Failure | gemma4:e4b | **数据失忆**。模型在浏览器看到了结果 '28'，但切到短信时丢失了具体数值。 |
| 2026-05-10 | (重试) 浏览器算 '2026-1998' 并短信发结果给 10086 | ✅ Success | gemma4:e4b | **治愈失忆**。通过 `scratchpad` 跨步记忆机制成功保持了数据流转。 |
| 2026-05-10 | 设置中查看 Android 版本并返回桌面 | ✅ Success | gemma4:e4b | 验证了深度导航、误触纠偏（Cancel 弹窗）和坐标盲狙能力。 |
| 2026-05-10 | 搜 NVIDIA 股价并短信发给 12345 | ✅ Success | gemma4:e4b | **终极纠偏**。克服了文字残留干扰，验证了“1.0s焦点等待”+“记忆传递”的组合威力。 |
| 2026-05-10 | (最终版) 搜 NVIDIA 股价并短信发给 12345 | ✅ Success | gemma4:e4b | 物理级稳定。在引入 `adb_type` 焦点等待后，跨应用打字一次成功，完美闭环。 |
| 2026-05-10 | 新号码 '13800138000' 开荒发验证码 9527 | ✅ Success | gemma4:e4b | **推门逻辑**。攻克了“输入号码后必须点建议项进场”的 UX 陷阱，结合物理全清，实现了零污染发送。 |

## 待解决问题 (Pending Issues)
- **跨应用数据持久化**：已通过 scratchpad 初步解决，需进一步压力测试。
- **Photos 右上角盲点**：部分高度自定义 UI 仍存在探测器黑洞。
- **UI 刷新延迟**：部分界面切换后 XML 刷新不及时，导致 ID 错位。

### Goal: 给12345发短信：终于搞定了中文输入
- **Status**: SUCCESS
- **Verification**: ADBKeyBoard successfully injected Chinese characters; verification step confirmed text appeared in message box.
- **Notes**: Chinese typing is now near-instant and reliable.

### Goal: 判断 typing+send 是否依赖 IME 弹出后的最新 XML
- **Status**: ANALYSIS ONLY
- **Verification**: Inspected `humanoid_agent.py`; `adb_type` performs tap, clear, input, and optional `ADB_EDITOR_CODE` in one function without re-dumping UI XML between typing and editor action.
- **Notes**: No code change. Proposed verification should compare IME editor-action send against visual click send under intentionally stale XML after keyboard-induced layout change.

### Goal: 用最小脚本验证 ADB_EDITOR_CODE 能否直接发送短信
- **Status**: SUCCESS
- **Verification**: Ran `python3 tests/verify_ime_editor_send.py --to 10086`; it opened the existing 10086 thread, tapped the message input, used `ADB_INPUT_TEXT`, then sent only `ADB_EDITOR_CODE 4` without clicking a visual send button.
- **Notes**: Final screenshot showed sent bubble `IME_TEST_1778468351`, the input box returned to `Text message`, and the script reported `PASS: ADB_EDITOR_CODE send submitted the message without clicking a visual send button.`

### Goal: 记录 ADB_EDITOR_CODE 发送短信经验
- **Status**: SUCCESS
- **Verification**: Appended the verified field note to `CHALLENGES.md` under Challenge 14.
- **Notes**: The note explicitly distinguishes "send button was clicked" from the actual result: no visual send click happened; `ADB_EDITOR_CODE 4` submitted the focused SMS input directly.
    true,
    true,
    true,
    true,
    false
  ],
  "notes_to_save": []
}
```

==================== STEP 5 [DECISION] [GEMMA] ====================
{
  "thought": "根据任务清单和已达成成就，短信发送操作已经成功完成。当前屏幕显示的是短信应用内部的对话界面，但总目标要求返回手机主屏幕（桌面）。因此，我需要执行返回到桌面的动作。",
  "action": "home",
  "id": null,
  "point": null,
  "text": "",
  "pkg": null,
  "seconds": 3
}
  "notes_to_save": [
    "短信内容：尊敬的客户，您的验证码是 9527，请勿泄露。"
  ]
}
```

==================== STEP 4 [DECISION] [GEMMA] ====================
{
  "thought": "根据上一步反馈，消息内容已成功输入到短信编辑框中，现在需要点击发送按钮来完成任务的第三步（发送成功）。由于当前截图没有直接显示发送按钮的 ID，我必须估算发送按钮在标准安卓短信应用界面底部的坐标。预计发送按钮位于屏幕底部右侧区域，点击该点将触发消息发送操作。",
  "action": "click",
  "id": null,
  "point": [
    950,
    2350
  ],
  "text": null,
  "editor_action": null,
  "pkg": null,
  "seconds": 3
}
