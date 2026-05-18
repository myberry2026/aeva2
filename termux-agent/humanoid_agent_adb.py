import time
import base64
import requests
import json
import os
import re
from datetime import datetime
from collections import defaultdict
from contextlib import contextmanager
# WebSocket 通道（用户中断 / 状态广播）拆到独立文件
from ws_channel import ws_poll
from output_channel import create_output

# 控制器架构（支持 ADB 和 Bridge 双后端）
from adb_utils import _adb_ensure_keyboard
from device_controller import ADBController, BridgeController
from bridge_client import BridgeClient
from tool_layer import inventory_diff, format_inventory_diff, stitch_images, render_checklist

# === 简单 profiling 工具 ===
# 每个 phase 在每步累加，跑完按 phase 汇总：总耗时、平均、调用次数
_PHASE_TIMES = defaultdict(list)
# Token usage 累加器（按 mode：DECISION / VERIFICATION / FINISH_CHECK / PLAN）
_USAGE_BY_MODE = defaultdict(lambda: {"prompt": 0, "completion": 0, "calls": 0})

# phase name → mode 映射，让 summary 表能把时间和 token 对齐展示
PHASE_TO_MODE = {
    "decision_llm": "DECISION",
    "verify_llm": "VERIFICATION",
    "finish_gate": "FINISH_CHECK",
}

def _record_usage(mode, usage):
    """从 agent_call 调用，累加 token 用量到全局表。"""
    if not usage: return
    bucket = _USAGE_BY_MODE[mode]
    bucket["prompt"] += int(usage.get("prompt_tokens") or 0)
    bucket["completion"] += int(usage.get("completion_tokens") or 0)
    bucket["calls"] += 1

@contextmanager
def profile(name, verbose=True):
    """用法: with profile('decision'): ... — 自动记录耗时，verbose=True 时单步也打印"""
    t0 = time.time()
    try:
        yield
    finally:
        dt = time.time() - t0
        _PHASE_TIMES[name].append(dt)
        if verbose:
            print(f"    ⏱️  [{name}] {dt:.2f}s")

def _print_phase_summary(wall_clock_sec=None, n_steps=None):
    """wall_clock_sec / n_steps: 可选，用于显示 dark time（wall - profiled）。"""
    if not _PHASE_TIMES and not _USAGE_BY_MODE: return
    print("\n" + "=" * 80)
    print("  ⏱️  分阶段耗时 + Token 汇总")
    print("=" * 80)
    print(f"   {'phase':18s} {'total':>8s} {'avg':>7s} {'n':>3s} {'%':>5s}   "
          f"{'in tok':>8s} {'out tok':>8s} {'in/call':>8s} {'out/call':>9s}")
    print("   " + "-" * 86)

    items = sorted(_PHASE_TIMES.items(), key=lambda x: -sum(x[1]))
    grand_total = sum(sum(v) for v in _PHASE_TIMES.values())
    total_in = 0
    total_out = 0
    for name, times in items:
        total = sum(times)
        n = len(times)
        avg = total / n
        pct = total / grand_total * 100 if grand_total > 0 else 0
        mode = PHASE_TO_MODE.get(name)
        u = _USAGE_BY_MODE.get(mode) if mode else None
        in_tok = u["prompt"] if u else 0
        out_tok = u["completion"] if u else 0
        in_per = (in_tok / u["calls"]) if u and u["calls"] else 0
        out_per = (out_tok / u["calls"]) if u and u["calls"] else 0
        total_in += in_tok
        total_out += out_tok
        in_str = f"{in_tok:>8d}" if in_tok else f"{'—':>8s}"
        out_str = f"{out_tok:>8d}" if out_tok else f"{'—':>8s}"
        in_per_str = f"{int(in_per):>8d}" if in_per else f"{'—':>8s}"
        out_per_str = f"{int(out_per):>9d}" if out_per else f"{'—':>9s}"
        print(f"   {name:18s} {total:7.1f}s {avg:6.2f}s {n:>3d} {pct:>4.1f}%   "
              f"{in_str} {out_str} {in_per_str} {out_per_str}")

    # 没对应 phase 的 mode（比如 PLAN）单独列
    used_modes = set(PHASE_TO_MODE.values())
    for mode, u in _USAGE_BY_MODE.items():
        if mode not in used_modes:
            total_in += u["prompt"]
            total_out += u["completion"]
            in_per = u["prompt"] / u["calls"] if u["calls"] else 0
            out_per = u["completion"] / u["calls"] if u["calls"] else 0
            print(f"   {mode + ' (only)':18s} {'—':>8s} {'—':>7s} {u['calls']:>3d} {'—':>5s}   "
                  f"{u['prompt']:>8d} {u['completion']:>8d} "
                  f"{int(in_per):>8d} {int(out_per):>9d}")

    print("   " + "-" * 86)
    print(f"   {'PROFILED TOTAL':18s} {grand_total:7.1f}s {'':>7s} {'':>3s} {'':>5s}   "
          f"{total_in:>8d} {total_out:>8d}")
    # Dark time = wall - profiled（sleep / adb action 没被 profile 包到的部分）
    if wall_clock_sec is not None:
        dark = wall_clock_sec - grand_total
        dark_pct = (dark / wall_clock_sec * 100) if wall_clock_sec > 0 else 0
        per_step_dark = (dark / n_steps) if n_steps else 0
        print(f"   {'WALL CLOCK':18s} {wall_clock_sec:7.1f}s")
        # Per-step 平均（最重要的横向对比视角：换不同 config 跑同步数任务时看这一行）
        if n_steps:
            wall_per = wall_clock_sec / n_steps
            in_per = total_in / n_steps
            out_per = total_out / n_steps
            print(f"   {'PER STEP AVG':18s} {wall_per:7.1f}s {'':>7s} {'n=':>3s} {n_steps:<3d}   "
                  f"{int(in_per):>8d} {int(out_per):>8d}  ← 横向对比看这行")
        print("   " + "-" * 86)
        print(f"   {'DARK TIME':18s} {dark:7.1f}s  ({dark_pct:.1f}%, "
              f"~{per_step_dark:.1f}s/step — sleep/adb/misc 没 profile 到的部分)")
    print("=" * 80 + "\n")

# 模型配置
MODEL_OPTIONS = {
    "GALLERY": {
        "url": os.getenv("GALLERY_URL", "http://localhost:8080") + "/v1/chat/completions",
        "model": "Gemma-4-E2B-it"
    },
    "OLLAMA": {
        "url": "http://localhost:11434/v1/chat/completions",
        "model": "gemma4:latest"
    },
    "REMOTE": {
        "url": "http://100.113.214.52:1234/v1/chat/completions",
        "model": "google/gemma-4-e4b"
    },
    "WIN": {
        "url": "http://127.0.0.1:1234/v1/chat/completions",
        "model": "google/gemma-4-e4b"
    },
}
CURRENT_MODEL = os.getenv("AGENT_MODEL", "REMOTE")

# 控制后端：adb（通过 USB/WiFi ADB 控制）或 bridge（通过 bridge-android 原生 app 控制）
CONTROL_BACKEND = os.getenv("CONTROL_BACKEND", "adb").lower()
assert CONTROL_BACKEND in ("adb", "bridge"), f"CONTROL_BACKEND must be adb/bridge, got {CONTROL_BACKEND!r}"

# 输出目标：overlay（手机浮窗）/ dashboard（终端 TUI）/ both（两个都发）
OUTPUT_TARGET = os.getenv("OUTPUT_TARGET", "dashboard").lower()
assert OUTPUT_TARGET in ("overlay", "dashboard", "both"), f"OUTPUT_TARGET must be overlay/dashboard/both, got {OUTPUT_TARGET!r}"

# bridge-android 配置（CONTROL_BACKEND=bridge 时使用）
BRIDGE_URL = os.getenv("BRIDGE_URL", "http://127.0.0.1:8765")
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "")
_hc = None  # lazy init in main()

def get_bridge_client() -> BridgeClient:
    """返回 Bridge 后端的底层 client（与 get_device() 共享同一实例）。"""
    global _hc
    if _hc is None:
        device = get_device()
        if hasattr(device, 'client'):
            _hc = device.client
        else:
            _hc = BridgeClient(BRIDGE_URL, BRIDGE_TOKEN)
    return _hc

# 决策时是否把 before+after 拼成一张大图喂模型。
# True:  一张拼接图（左 BEFORE / 右 AFTER），空间关系明确，但单图分辨率被压缩
# False: 两张独立图，分辨率保留，但模型需自己理解顺序
VERIFY_STITCH = os.getenv("VERIFY_STITCH", "false").lower() == "true"

# 核验模式：xml / images / both
#   xml    - 只送 UI 元素 diff 文本，不送截图（最快，但失去视觉确认）
#   images - 只送 before+after 双图（当前默认行为，无 deterministic 锚点）
#   both   - 同时送图 + UI diff（信息最全，反 hallucination 最强）
VERIFY_MODE = os.getenv("VERIFY_MODE", "both").lower()
assert VERIFY_MODE in ("xml", "images", "both"), f"VERIFY_MODE must be xml/images/both, got {VERIFY_MODE!r}"

# 全局路径，在 main() 中初始化
RUN_DIR = "logs"
LOG_FILE = "logs/agent_debug.log"
RESP_FILE = "logs/agent_responses.log"
PLAN_CACHE_FILE = "logs/plan_cache.json"

def log(msg):
    print(f"[*] {msg}")

def save_debug_log(step, mode, prompt, response, usage=None):
    # Ensure response is a string for logging
    raw_res = str(response) if response is not None else "<EMPTY RESPONSE>"

    # Try to pretty print JSON response
    formatted_response = raw_res
    try:
        if response and isinstance(response, str) and (response.strip().startswith('{') or response.strip().startswith('[')):
            data = json.loads(response)
            formatted_response = json.dumps(data, indent=2, ensure_ascii=False)
    except:
        pass

    # 写入完整调试日志（含 Prompt）
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*20} STEP {step} [{mode}] [{CURRENT_MODEL}] {'='*20}\n")
        if usage:
            f.write(f"[USAGE]: {json.dumps(usage, ensure_ascii=False)}\n")
        f.write(f"[PROMPT]:\n{prompt}\n")
        f.write(f"\n[RESPONSE]:\n{formatted_response}\n")

    # 写入纯模型响应日志
    with open(RESP_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*20} STEP {step} [{mode}] [{CURRENT_MODEL}] {'='*20}\n")
        if usage:
            f.write(f"[USAGE]: {json.dumps(usage)}\n")
        f.write(formatted_response + "\n")

    # Also log to console for visibility
    if usage:
        u_str = f"{usage.get('prompt_tokens','?')}/{usage.get('completion_tokens','?')}/{usage.get('total_tokens','?')}"
        log(f"[{mode}] Response received. Usage(in/out/total): {u_str}")
    else:
        log(f"[{mode}] Response received from {CURRENT_MODEL}.")
    if formatted_response and formatted_response != "<EMPTY RESPONSE>":
        # 只打印前 500 个字符避免刷屏，完整的在 log 文件里
        print(formatted_response[:500] + ("..." if len(formatted_response) > 500 else ""))
    else:
        log(f"⚠️  [{mode}] 收到空响应或无效响应")

# --- 控制层：双 backend 支持 (adb / bridge) ---

SCREEN_W, SCREEN_H = 1080, 2400  # main() 启动时会刷新

# === 全局控制器实例（在 main() 中初始化） ===
_device = None

def get_device():
    global _device
    if _device is None:
        if CONTROL_BACKEND == "bridge":
            _device = BridgeController(BRIDGE_URL, BRIDGE_TOKEN)
        else:
            _device = ADBController()
    return _device

def adb_wait(seconds):
    time.sleep(seconds)


# --- Agent 交互 ---


def agent_call(prompt, images, step, mode, stitch=False):
    """
    通过 OpenAI 兼容接口调用模型，支持图片 and Chat 格式。
    """
    config = MODEL_OPTIONS[CURRENT_MODEL]
    url = config["url"]
    model_name = config["model"]

    if isinstance(images, str): images = [images]
    if stitch and len(images) > 1:
        stitched_path = f"{RUN_DIR}/_stitched_step_{step}_{mode}.png"
        stitch_images(images, stitched_path, axis="horizontal", label=True)
        images = [stitched_path]
    
    # 构造消息内容
    # Gemma 多模态：图片必须放在 text 前面，否则 vision grounding 显著下降
    system_msg = {"role": "system", "content": "You are a specialized Android automation robot. Do NOT think, do NOT reason, and do NOT output any preamble. Output ONLY the raw JSON structure."}
    user_content = []
    for p in images:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"}
            })
    user_content.append({"type": "text", "text": prompt})

    payload = {
        "model": model_name,
        "messages": [
            system_msg,
            {"role": "user", "content": user_content}
        ],
        "stream": False,
        "temperature": 1.0, # 官方推荐
        "top_p": 0.95,
        "top_k": 64
    }
    
    payload_json = json.dumps(payload)
    log(f"   [LLM] 发送请求 ({mode})... Payload 大小: {len(payload_json)/1024:.1f} KB")
    
    t_start = time.time()
    res_text = None
    usage = None
    try:
        r = requests.post(url, json=payload, timeout=60) # 缩短超时到 60s
        dt = time.time() - t_start
        log(f"   [LLM] 收到响应! 耗时: {dt:.2f}s, 状态码: {r.status_code}")
        r.raise_for_status()
        res_json = r.json()
        res_text = res_json['choices'][0]['message'].get("content", "")
        usage = res_json.get("usage")
        _record_usage(mode, usage)  # 累加到全局，供 _print_phase_summary 用
        save_debug_log(step, mode, prompt, res_text, usage=usage)

        # 鲁棒解析 JSON：用 raw_decode 只解析第一个完整对象，自动忽略后面的 trailing 数据
        # （修复 bug：模型有时输出两个连续 JSON，贪婪正则会把它们拼一起 → "Extra data" 错误）
        if res_text:
            start = res_text.find('{')
            if start >= 0:
                try:
                    obj, _end = json.JSONDecoder().raw_decode(res_text[start:])
                    return obj
                except json.JSONDecodeError as e:
                    log(f"[{mode}] JSON raw_decode 失败: {e}")
                    # 兜底：尝试非贪婪正则匹配最小 JSON
                    match = re.search(r'\{.*?\}', res_text, re.DOTALL)
                    if match:
                        try:
                            return json.loads(match.group())
                        except Exception:
                            pass
        return None
    except Exception as e:
        log(f"[{mode}] 调用失败: {e}")
        save_debug_log(step, mode, prompt, f"<ERROR> {e}\nRAW: {res_text}", usage=usage)
        return None

def get_plan_from_cache(final_goal):
    if not os.path.exists(PLAN_CACHE_FILE): return None
    try:
        with open(PLAN_CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
            return cache.get(final_goal)
    except: return None

def save_plan_to_cache(final_goal, plan):
    cache = {}
    if os.path.exists(PLAN_CACHE_FILE):
        try:
            with open(PLAN_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except: pass
    cache[final_goal] = plan
    try:
        with open(PLAN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except: pass

def plan_call(final_goal, step=0):
    """把总目标拆成有序的原子子任务清单。带缓存。"""
    # 尝试从缓存读取
    cached = get_plan_from_cache(final_goal)
    if cached:
        log("发现缓存的 PLAN，跳过 LLM 调用。")
        return cached

    prompt = f"""你是一个 Android 自动化任务规划专家。

【总目标】: {final_goal}

请把总目标拆成【成功状态条件】清单（不是动作步骤！），满足：
1. 每条 ≤25 字，描述一个【可观察到的状态/结果】，而不是要做的动作
   ❌ 错："点击搜索按钮" / "进入详情页"（这是动作）
   ✅ 对："屏幕显示搜索结果列表" / "屏幕上看到了电话号码"（这是状态）
2. 每条必须可以通过单张截图肉眼判断 true/false
3. 状态条件 once-true-stays-true（达到过就视为完成，不会因为后续页面切换变 false）
4. 总数 3-8 条之间
5. 包含起始/收尾的状态条件

【严格禁令】:
- 严禁使用任何 LaTeX 符号（如 \\ge, \\le, \\times）。
- 严禁在 JSON 字符串中使用反斜杠 "\\"。
- 数学符号请用普通文本替代，如 ">= 4.6"。

示例（目标："在地图搜披萨找 4.6+ 的店点 Call 然后回主页"）：
{{"plan": [
  "当前在地图 app 内",
  "看到过 'best pizza' 搜索结果列表",
  "看到过评分 >= 4.6 的店出现在屏幕",
  "看到过该店的电话号码（详情页或拨号界面）",
  "回到了地图主页"
]}}

注意上面每条都是【状态描述】——只要这个状态在执行过程中【任何时刻】被达到过就算 true，不管走哪条路径达到。

返回 JSON（不要 markdown 包裹）:
{{"plan": ["状态条件1", "状态条件2", "..."]}}
"""
    res = agent_call(prompt, [], step, "PLAN")
    if not res: return None
    plan = res.get("plan")
    if not isinstance(plan, list) or not plan: return None
    cleaned = [str(s).strip() for s in plan if str(s).strip()][:8]
    if cleaned:
        save_plan_to_cache(final_goal, cleaned)
    return cleaned or None


def run_finish_gate(step, final_goal, plan, plan_state, scratchpad=None, trigger_reason=""):
    """二次核验门：截图 + checklist + scratchpad → 模型审计是否真的完成。返回 (passed, evidence)。"""
    log(f"进入 FINISH_CHECK 二次核验...（触发: {trigger_reason or '模型自报 finish'}）")
    time.sleep(2)
    suffix = "_auto" if trigger_reason else ""
    pic_check = f"{RUN_DIR}/step_{step}_finish_check{suffix}.png"
    get_device().take_screenshot(pic_check)
    checklist = render_checklist(plan, plan_state)
    done_count = sum(plan_state)
    scratchpad_text = "\n".join(f"- {s}" for s in scratchpad) if scratchpad else "（无）"
    check_prompt = f"""
你是一个高级审计专家。当前判定任务【可能已完成】。

【总目标】: {final_goal}

【任务清单与状态】（{done_count}/{len(plan)} 已完成）:
{checklist}

【执行过程记录（scratchpad，含用户口头补充/插话）】:
{scratchpad_text}

【当前截图】: 见附图

请审查：
1. 清单上所有 [x] 标记的子任务，是否真的与历史执行相符？是否有虚假打勾？
2. 当前截图是否符合任务结束时应处的页面？
3. 如果清单全部 [x] 且当前截图合理，判 true。
4. 如果有用户输入，以用户的判断为最高优先级，用户的最新要求可以覆盖原有要求，甚至提前结束任务。Evidence 可以是用户最新的要求。

返回 JSON:
{{ "truly_done": bool, "evidence": "≤60字 审计结论" }}
"""
    check = agent_call(check_prompt, pic_check, step, "FINISH_CHECK")
    if check and check.get('truly_done'):
        return True, check.get('evidence', '无')
    return False, (check.get('evidence', '核验未返回') if check else '核验调用失败')

def _print_run_summary(final_goal, plan, plan_state, scratchpad, steps_taken, status, elapsed_sec):
    """跑完后打印一份漂亮的总结，方便 demo 现场看战绩。"""
    print("\n" + "=" * 60)
    print(f"  任务结束 — {status}")
    print("=" * 60)
    print(f"🎯 总目标: {final_goal}")
    print(f"📊 Plan 进度: {sum(plan_state)}/{len(plan)}")
    for i, (t, d) in enumerate(zip(plan, plan_state)):
        marker = "✅" if d else "❌"
        print(f"   {marker} {i+1}. {t}")
    if scratchpad:
        print(f"📝 Scratchpad ({len(scratchpad)} 条):")
        for n in scratchpad:
            print(f"   - {n}")
    print(f"⏱️  共执行 {steps_taken} 步 / 耗时 {elapsed_sec}s")
    print("=" * 60 + "\n")

def main(final_goal=None):
    global SCREEN_W, SCREEN_H, LOG_FILE, RESP_FILE, RUN_DIR
    print(">>> [DEBUG] Entering main()...", flush=True)
    
    # 初始化环境
    log(f"控制后端: {CONTROL_BACKEND}")
    if CONTROL_BACKEND == "bridge":
        hc = get_bridge_client()
        if not hc.is_ready():
            log("⚠️  bridge 未就绪，请确认 bridge-android app 已启动且 AX service 已开启")
            log(f"   尝试连接: {BRIDGE_URL}")
        else:
            log(f"✅ bridge 已连接: {BRIDGE_URL}")
    else:
        _adb_ensure_keyboard()

    # 检查 LLM 端点
    m_cfg = MODEL_OPTIONS.get(CURRENT_MODEL, {})
    m_url = m_cfg.get("url", "")
    log(f"模型后端: {CURRENT_MODEL} ({m_url})")
    try:
        # 尝试简短的健康检查（/health 是 EmbeddedLlmServer 提供的）
        health_url = m_url.replace("/v1/chat/completions", "/health")
        r = requests.get(health_url, timeout=3)
        if r.status_code == 200:
            log(f"✅ 模型服务器已就绪: {r.json().get('status', 'ok')}")
        else:
            log(f"⚠️  模型服务器响应异常: {r.status_code}")
    except Exception as e:
        log(f"⚠️  无法连接模型服务器: {e}")
        log("   请确认 Bridge App 中的 LLM Server 已启动 (8080)")

    # 输出通道：overlay / dashboard / both
    _bc = get_bridge_client() if CONTROL_BACKEND == "bridge" else None
    _output = create_output(OUTPUT_TARGET, bridge_client=_bc,
                            ws_port=int(os.getenv("WS_PORT", "8768")))
    _output.start()
    _output.reset()

    def _overlay(text, snapshot=None):
        """发送状态到输出通道。"""
        try:
            _output.send_state(text, snapshot or {})
        except Exception:
            pass
    
    # 每次运行生成唯一的运行目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    RUN_DIR = f"logs/run_{timestamp}"
    os.makedirs(RUN_DIR, exist_ok=True)

    LOG_FILE = f"{RUN_DIR}/agent_debug.log"
    RESP_FILE = f"{RUN_DIR}/agent_responses.log"
    
    if final_goal is None:
        final_goal = "在地图搜索 'best pizza in San Francisco'，滚动寻找一家评分 >= 4.6 的店点进去，拿到电话号码，最后退回地图主页。"
    log("=== 启动【强反馈决策版】Agent 7.6（通用型）===")
    log(f"目标: {final_goal}")
    SCREEN_W, SCREEN_H = get_device().get_screen_size()
    log(f"屏幕尺寸: {SCREEN_W}x{SCREEN_H}")

    # === 环境检查 ===
    installed_apps = get_device().get_installed_apps()
    log(f"已发现 {len(installed_apps)} 个 launcher app（prefetch）")
    apps_str = ", ".join(installed_apps) if installed_apps else "(prefetch 失败，open_app 时凭经验填包名)"

    # === Plan 阶段：把目标拆成 checklist ===
    log("=== PLAN 阶段：拆解任务 ===")
    with profile("plan_llm"):
        plan = plan_call(final_goal)
    if not plan:
        log("⚠️  PLAN 调用失败，退化为单项 plan（整个目标作为一条）")
        plan = [final_goal]
    plan_state = [False] * len(plan)
    log("任务拆解完成：")
    for i, t in enumerate(plan):
        log(f"  {i+1}. {t}")

    last_verify_result = "Task started. Check screen and navigate if needed."
    consecutive_fails = 0
    scratchpad = []  # 跨步事实记忆：电话号码 / 价格 / 名字 / 地址等具体信息
    SCRATCHPAD_MAX = 20

    # Stuck-on-focus 检测：focus_idx 同一项连续 N 步没动 → home 兜底
    last_focus_idx = -2  # 故意不等于任何合法值，初始触发"换 focus" 逻辑
    focus_stuck_count = 0
    FOCUS_STUCK_THRESHOLD = 4

    # 跑完总结用
    run_status = "STEPS_EXHAUSTED"
    steps_taken = 0
    start_time = time.time()

    # 用于 dashboard：最近 thought + verify 多字段
    last_thought = ""
    current_target = ""
    last_action_success = None       # 上一步 verify 的 bool
    last_reflection = ""             # verify reflection（解释 action_success）
    last_mission_complete = None     # 上一步 verify 的整体 done bool
    last_mission_reason = ""         # 解释 mission_complete
    last_progress = ""               # 这一步带来的 progress

    def _snapshot_state():
        """构造一份完整 dashboard state 给 ws_broadcast 用。"""
        prof_total = sum(sum(v) for v in _PHASE_TIMES.values())
        llm_total = sum(sum(v) for k, v in _PHASE_TIMES.items() if k.endswith("_llm") or k == "finish_gate")
        in_tok = sum(u["prompt"] for u in _USAGE_BY_MODE.values())
        out_tok = sum(u["completion"] for u in _USAGE_BY_MODE.values())
        focus = next((i for i, d in enumerate(plan_state) if not d), -1)
        return {
            "type": "state",
            "goal": final_goal,
            "step": steps_taken,
            "max_steps": 15,
            "status": run_status,
            "elapsed": int(time.time() - start_time),
            "model": CURRENT_MODEL,
            "plan": plan,
            "plan_state": list(plan_state),
            "focus_idx": focus,
            "scratchpad": list(scratchpad),
            "last_thought": last_thought,                       # 完整 thought 不截断
            "last_verify": last_verify_result[:400],            # 截短防爆但放宽到 400
            "current_target": current_target,
            # 新增 verify 子字段（dashboard 分行显示）
            "last_action_success": last_action_success,
            "last_reflection": last_reflection,
            "last_mission_complete": last_mission_complete,
            "last_mission_reason": last_mission_reason,
            "last_progress": last_progress,
            "profile": {
                "wall": int(time.time() - start_time),
                "profiled": round(prof_total, 1),
                "llm": round(llm_total, 1),
                "in_tok": in_tok,
                "out_tok": out_tok,
            },
        }

    # 📡 Plan 出来后立刻发 overlay（dashboard 初始化）
    _overlay(f"📋 {final_goal}\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(plan)),
             snapshot=_snapshot_state())

    # === HACK 模拟用户插话（debug 用，默认关闭；设 HACK_INJECT_AT_STEP=N 启用）===
    HACK_INJECT_AT_STEP = int(os.getenv("HACK_INJECT_AT_STEP", "999"))
    HACK_INJECT_MSG = os.getenv("HACK_INJECT_MSG",
        "不用等系统确认了，短信已经发出去就算完成。请直接 finish。")
    hack_injected = False

    def _apply_user_interrupt(text, step, source="WS"):
        """统一处理用户插话：scratchpad 加一条 + 构造 last_verify_result 顶部告警。"""
        scratchpad.append(f"[⚠️ USER 插话 ({source}) @ step {step}] {text}")
        return (
            f"⚠️⚠️⚠️ 用户刚刚 ({source}) 插话：「{text}」\n"
            f"请优先响应用户指令，如果有用户输入，以用户的判断为最高优先级，用户的最新要求可以覆盖原有要求——比如对应 criterion 不可观测但用户授权了，"
            f"把对应 subtasks_status 设 true 或直接 action='finish'。\n\n"
            f"上一步原本反馈：{last_verify_result}"
        )

    # 📡 #1 Plan 出来后立刻广播一次（dashboard 初始化）
    _output.send_state("", _snapshot_state())

    last_event_timestamp = int(time.time() * 1000)

    # Force return to home screen before starting the first step
    log("🏠 Forcing back to home screen before starting task...")
    get_device().home()
    time.sleep(2)

    for step in range(1, 16):
        steps_taken = step

        # 1) 优先消费用户插话（real-time）
        user_text = None
        source = None
        
        ws_msg = ws_poll()
        if ws_msg:
            user_text = ws_msg.get("text") or ws_msg.get("msg") or json.dumps(ws_msg, ensure_ascii=False)
            source = "WS"
            
        if CONTROL_BACKEND == "bridge":
            try:
                hc = get_bridge_client()
                events_resp = hc.poll_events(since=last_event_timestamp)
                events = events_resp.get("events", [])
                for ev in events:
                    if ev.get("timestamp", 0) > last_event_timestamp:
                        last_event_timestamp = ev["timestamp"]
                    if ev.get("eventType") == "voice_final" and ev.get("text"):
                        user_text = ev["text"]
                        source = "VOICE"
            except Exception as e:
                log(f"⚠️ Error polling events: {e}")

        if user_text:
            log(f"\n{'🎤'*20}")
            log(f"🎤 USER (via {source}) @ step {step}: {user_text}")
            log(f"{'🎤'*20}\n")
            last_verify_result = _apply_user_interrupt(user_text, step, source=source)
            # 📡 #5 推一个 event，dashboard 可以闪烁用户区
            _output.send_event({"type": "event", "kind": "user_input", "text": user_text, "step": step})
            _output.send_state("", _snapshot_state())

        # 2) HACK fallback：开发期模拟用户插话（HACK_INJECT_AT_STEP=N 启用）
        if step > HACK_INJECT_AT_STEP and not hack_injected:
            log(f"\n{'🔧'*20}")
            log(f"🔧 [HACK] 模拟用户在 step {step} 插话: {HACK_INJECT_MSG}")
            log(f"{'🔧'*20}\n")
            last_verify_result = _apply_user_interrupt(HACK_INJECT_MSG, step, source="HACK")
            hack_injected = True

        pic_before = f"{RUN_DIR}/step_{step}_before.png"
        with profile("screenshot_before"):
            get_device().take_screenshot(pic_before)
        with profile("ui_dump"):
            elements = get_device().get_inventory()
        list_str = "\n".join([f"ID {e['id']}: '{e['label']}' @ {e['pos']}" for e in elements])
        focus_idx = next((idx for idx, d in enumerate(plan_state) if not d), -1)
        checklist = render_checklist(plan, plan_state, focus_idx)
        focus_task = plan[focus_idx] if focus_idx >= 0 else "（全部已完成）"

        log(f"\n--- 第 {step} 步：决策阶段 [{sum(plan_state)}/{len(plan)}] ---")
        overlay_text = f"🎯 {final_goal}\n" + "-"*15 + "\n" + checklist
        _overlay(overlay_text, snapshot=_snapshot_state())


        done_str = ", ".join([plan[i] for i, d in enumerate(plan_state) if d]) if any(plan_state) else "无"
        prompt_decide = f"""
你是一个 Android 自动化专家，正在驱动一台真实手机。
当前屏幕真实分辨率: {SCREEN_W} x {SCREEN_H} (所有坐标点 [x, y] 必须在此范围内)

【总目标】: {final_goal}
【已达成成就】: {done_str}

【任务清单】（[x]=已完成 [→]=当前焦点 [ ]=待办）:
{checklist}
【当前焦点子任务】: {focus_task}

【scratchpad - 跨步记忆的事实信息】（{len(scratchpad)} 条，可直接引用，例如发短信时引用电话号码）:
{chr(10).join(f"- {n}" for n in scratchpad) if scratchpad else "（暂无记录）"}

【上一步执行反馈】:
{last_verify_result}

【本机已安装应用（open_app 时从中选 pkg）】:
{apps_str}

【当前可交互清单】（注意：ID 仅本步有效，跨步引用请用 label 而非 ID）:
{list_str}

【Gap 分析要求】：
1. 当前截图处于哪个 app / 页面？是否已经在目标 app？没有的话先 open_app。
2. 刚才那一步生效了吗？没生效的根因是什么？
3. 离总目标还差什么？**请对比【总目标】与【已达成成就】，严禁重复执行已完成的步骤。**
4. 如果目标已达成，请果断执行 "finish" 动作，不要因为页面细节微差而尝试重新开始。
5. 【兜底坐标点击】优先用 id；只有当目标元素（小图标、自定义 UI、Photos 选择器的 Done 等）在【当前可交互清单】中确实找不到时，才改用 `point: [x, y]` 直接给坐标。若用 point，请在 thought 中说明坐标是怎么估算的。

必须返回以下 JSON 格式（不要返回 markdown 包裹）:
{{
  "thought": "按照分析要求来。必须给出动作理由，但禁止复述总目标全文。最后给出接下来的动作，以及为什么想这么做",
  "action": "click" | "type" | "scroll_down" | "scroll_up" | "back" | "home" | "open_app" | "long_press" | "wait" | "finish",
  "id": ID数字（仅 click/type/long_press 需要；清单里能找到就必填此字段而不是 point）,
  "point": [x, y]（仅当清单里找不到目标 ID 时备用，单位像素，必须在屏幕范围内）,
  "text": "输入内容（仅 type 需要）",
  "editor_action": "搜索/发送/完成等动作（仅 type 时可选）。可选值: 'search' | 'send' | 'done' | 'go' | 'next' | 'previous' | null。搜索框填 'search'，消息发送填 'send'，普通文本框填 null。比裸 Enter 键稳得多。",
  "pkg": "包名（仅 open_app 需要，必须是上面已安装清单里的）",
  "seconds": 3
}}
"""
        with profile("decision_llm"):
            decision = agent_call(prompt_decide, pic_before, step, "DECISION")
        if not decision:
            last_verify_result = "上一步决策调用失败（模型无响应或返回非 JSON）。请重试一个简单稳妥的动作（如 wait 或 home）。"
            consecutive_fails += 1
            log("决策返回空，跳过执行")
            if consecutive_fails >= 3:
                log("⚠️  连续 3 次失败，触发兜底：home")
                get_device().home(); time.sleep(2)
                last_verify_result = "连续多步失败已触发兜底（已返回桌面），请重新规划，从 open_app 开始。"
                consecutive_fails = 0
            time.sleep(2)
            continue

        print("\n" + ">"*10 + " AI 深度 Gap 分析 " + "<"*10)
        print(decision.get('thought', '分析中...'))
        print(">"*35 + "\n")

        # 📡 #2 decision 出来后广播：dashboard 看到完整 thought + 即将做的 action
        last_thought = (decision.get('thought') or "").strip()  # 不截断，让 dashboard 自己 wrap
        
        if CONTROL_BACKEND == "bridge" and last_thought:
            try:
                get_bridge_client().send_chat_message("agent", last_thought, is_markdown=True)
            except Exception as e:
                log(f"⚠️ Error sending thought to Chat UI: {e}")
            _overlay(f"🎯 {final_goal}\n" + "-"*15 + "\n" + checklist + f"\n\n🤔 思考: {last_thought}",
                     snapshot=_snapshot_state())

        # current_target 多附 text/point 信息
        _act = decision.get('action', '?')
        _id = decision.get('id')
        _pt = decision.get('point')
        _txt = decision.get('text')
        _parts = [_act]
        if _id is not None: _parts.append(f"id={_id}")
        if _pt: _parts.append(f"pt={_pt}")
        if _txt: _parts.append(f'text="{_txt[:30]}"')
        current_target = " ".join(_parts)
        # ws_broadcast(_snapshot_state())

        act = decision.get("action")
        target_label = "N/A"
        exec_error = None
        finish_requested = False

        def _resolve_target(d):
            # 优先 ID 逻辑
            i = d.get('id')
            if isinstance(i, int) and 0 <= i < len(elements):
                e = elements[i]
                return e['pos'], e['label']

            # 备选 Point 逻辑（带屏幕边界 clamp，防止模型返回越界坐标导致 ghost click）
            p = d.get('point')
            if isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p):
                clamped = [
                    max(0, min(SCREEN_W - 1, int(p[0]))),
                    max(0, min(SCREEN_H - 1, int(p[1]))),
                ]
                if clamped != [int(p[0]), int(p[1])]:
                    log(f"⚠️  point {p} 越界，clamp 到 {clamped}（屏幕 {SCREEN_W}x{SCREEN_H}）")
                return clamped, f"坐标点 {clamped}"

            # 如果是无目标动作
            if d.get('action') in ["scroll_down", "scroll_up", "back", "home", "open_app", "wait", "finish"]:
                return None, "系统/全局"

            # 严厉具体反馈：分两个 case
            if i is None:
                raise ValueError("该动作要求提供 ID，但你返回了 id: null（也未提供 point 备选）。请在【当前可交互清单】中准确寻找目标元素的 ID；若清单里确实没有，请在 point 字段给出截图估算的坐标。")
            raise IndexError(f"id={i!r} 越界（清单仅 {len(elements)} 项）")

        try:
            target_pos, target_label = _resolve_target(decision)
            with profile(f"action_{act}"):  # 按动作类型分别测耗时
                log(f"[*] 正在调用动作指令: {act} (目标: {target_label})")
                if act == "click": get_device().tap(*target_pos)
                elif act == "type": get_device().tap_and_type(target_pos[0], target_pos[1], decision.get('text', ''), editor_action=decision.get('editor_action'))
                elif act == "long_press": get_device().long_press(*target_pos)
                elif act == "scroll_down": get_device().swipe(SCREEN_W//2, SCREEN_H*3//4, SCREEN_W//2, SCREEN_H//4)
                elif act == "scroll_up": get_device().swipe(SCREEN_W//2, SCREEN_H//4, SCREEN_W//2, SCREEN_H*3//4)
                elif act == "back": get_device().back(); target_label = "系统"
                elif act == "home": get_device().home(); target_label = "系统"
                elif act == "open_app":
                    pkg = decision.get('pkg')
                    if not pkg:
                        exec_error = "open_app 缺少 pkg 字段"
                    else:
                        if installed_apps and pkg not in installed_apps:
                            log(f"⚠️  pkg {pkg!r} 不在安装清单内，仍尝试启动")
                        log(f"[*] 正在请求打开包名: {pkg}")
                        get_device().open_app(pkg); target_label = pkg
                elif act == "wait": adb_wait(decision.get('seconds', 3)); target_label = "等待"
                elif act == "finish": finish_requested = True; target_label = "（声明完成）"
                else: exec_error = f"未知动作: {act!r}"
                log(f"[*] 动作指令 {act} 已发出")
        except (IndexError, KeyError, TypeError, ValueError) as e:
            exec_error = f"{type(e).__name__}: {e}"
            log(f"执行出错: {exec_error}")

        # --- finish 二次核验门（模型主动 finish）---
        if finish_requested:
            with profile("finish_gate"):
                passed, ev = run_finish_gate(step, final_goal, plan, plan_state, scratchpad=scratchpad)
            if passed:
                log(f"✅ 目标确认达成！证据: {ev}")
                run_status = "SUCCESS (模型主动 finish)"
                break
            log(f"❌ finish 核验未通过: {ev}")
            last_verify_result = f"模型声明 finish 但二次核验未通过。证据: {ev}。请继续推进未完成子任务。"
            consecutive_fails += 1
            time.sleep(2)
            continue

        # --- 核验步：根据 VERIFY_MODE 决定送图 / XML / both ---
        time.sleep(4)
        log(f"--- 第 {step} 步：结果核验（模式={VERIFY_MODE}）---")
        pic_after = f"{RUN_DIR}/step_{step}_after.png"

        # 截图（xml-only 模式也截，作为 finish_gate 备用 + 调试存档）
        with profile("screenshot_after"):
            get_device().take_screenshot(pic_after)

        # UI inventory after + diff（xml / both 模式需要）
        elements_diff_text = ""
        if VERIFY_MODE in ("xml", "both"):
            with profile("ui_dump_after"):
                elements_after = get_device().get_inventory()
            diff = inventory_diff(elements, elements_after)
            elements_diff_text = format_inventory_diff(diff)
            log(f"      🔍 UI diff: 新出现 {len(diff['appeared'])}, 消失 {len(diff['disappeared'])}")

        # 根据模式构造图片描述 + 是否传图
        if VERIFY_MODE == "xml":
            img_desc = "本次核验【纯 XML 模式】：没有截图，只看 UI 元素的程序级变化判断。"
            verify_images = []
        elif VERIFY_STITCH:
            img_desc = "我会传一张拼接图给你：左半边是【动作前 BEFORE】，右半边是【动作后 AFTER】。"
            verify_images = [pic_before, pic_after]
        else:
            img_desc = "我会传两张图给你：第一张是【动作前 BEFORE】，第二张是【动作后 AFTER】。"
            verify_images = [pic_before, pic_after]

        # UI section（xml / both 模式才有）
        # 不光给 diff，连 BEFORE 完整 inventory 一起给——让模型有 context 推理"啥变了"
        # （diff 单独看可能歧义："Call 消失" 是好是坏？看 before 是不是预期看到 Call 才知道）
        if VERIFY_MODE in ("xml", "both"):
            ui_diff_section = f"""
【BEFORE UI inventory（动作前的完整元素清单）】（ID 仅 BEFORE 时刻有效）:
{list_str}

【UI 元素变化（程序检测，确定性真相，AFTER vs BEFORE）】:
{elements_diff_text}
"""
        else:
            ui_diff_section = ""

        done_str_v = ", ".join([plan[i] for i, d in enumerate(plan_state) if d]) if any(plan_state) else "无"
        plan_lines = "\n".join([f'  {i+1}. [{("x" if plan_state[i] else " ")}] {t}' for i, t in enumerate(plan)])
        scratchpad_text_v = "\n".join(f"- {s}" for s in scratchpad) if scratchpad else "（无）"
        prompt_verify = f"""
【总目标】: {final_goal}
【目前已记录的关键里程碑】: {done_str_v}

【任务状态清单】（每条是【可观察状态】，不是动作；once-true-stays-true）:
{plan_lines}

【执行过程记录（scratchpad，含用户口头补充/插话）】:
{scratchpad_text_v}
{ui_diff_section}
刚才尝试对 '{target_label}' 做了 '{act}'。
{img_desc}
请严格对比 BEFORE 和 AFTER 回答：
1. 这一步动作 (action_success)：界面是否朝目标方向变化了？该步是否生效？给出 reflection 解释。
2. 这一步如果实质推进了目标，把里程碑写进 progress。
3. 整个任务 (mission_complete)：对照【总目标】，所有子环节（含收尾步骤）是否已全部完成？给出 mission_reason 解释。
4. subtasks_status：对照上面【任务状态清单】，**返回与清单一一对应的完整 boolean 数组**，长度必须 = {len(plan)}。
   - 第 i 个 bool = 当前【或之前任意时刻】是否观察到第 i+1 条状态条件成立
   - 已经是 [x] 的格子继续填 true（once-true-stays-true）
   - 这一步刚观察到的也填 true
   - 必须有视觉证据，不能凭推测；模糊不清填 false

⚠️ 字段规则：
- `action_success` vs `mission_complete` 是两件事：
   * action_success = 这一步动作生效了吗（局部）
   * mission_complete = 整个总目标全部达成了吗（全局）
   * 一步动作可以成功，但任务还远没完成 → action_success=true, mission_complete=false
- `progress`：单个字符串。这一步带来的【真实进展】，例如：
   * "进入了搜索结果列表" / "成功输入搜索词 'best pizza'" / "成功打开店铺详情页" / "成功触发拨号界面"
   * 如果只是误回退/与目标无关的页面跳转/纯等待，填空字符串 ""
- `remaining_gap`：只写还没做的【具体下一步动作】，禁止复述总目标全文。mission_complete=true 时填 "None"。
- `notes_to_save`：如果这一步看到了【具体的事实/数字/名字/号码/地址/价格】，且后续步骤可能要用（如发短信引用、跨 app 拼接）, 把它存进 scratchpad。
   * 每条字符串 ≤30 字，**必须自带 context**（"今日金价 $2050" 不是 "$2050"；"Sforno 电话 415-347-5881" 不是 "415-347-5881"）
   * 只存【看到的事实】，不存【你的推理】
   * 没有具体事实要记 → 填 []
   * 例：["今日金价 $2050"]、["Sforno 4.7分 电话 415-347-5881"]、["天气：明天旧金山 18°C 多云"]

返回 JSON（按顺序填）:
{{
  "action_success": bool,
  "reflection": "≤40字 解释 action_success 的判断理由（看到什么变化/没变化）",
  "progress": "≤30字 这一步的真实进展，无则填空字符串",
  "remaining_gap": "还差什么具体动作",
  "mission_complete": bool,
  "mission_reason": "≤40字 解释 mission_complete 的判断理由（哪些环节已做完/还差什么环节）",
  "subtasks_status": [{", ".join(["bool"] * len(plan))}],
  "notes_to_save": []
}}
"""
        with profile("verify_llm"):
            # stitch 只有在 images 模式且双图时才有意义；xml 模式没图
            do_stitch = VERIFY_STITCH and len(verify_images) > 1
            verification = agent_call(prompt_verify, verify_images, step, "VERIFICATION", stitch=do_stitch)

        if verification:
            success = verification.get('action_success', False)
            mission_complete = verification.get('mission_complete', False)
            reflection = verification.get('reflection', '（模型未返回 reflection）')
            mission_reason = verification.get('mission_reason', '（模型未返回 mission_reason）')
            _overlay(f"{'✓' if success else '✗'} {act} → {reflection[:50]}",
                     snapshot=_snapshot_state())
            remaining = verification.get('remaining_gap', '（模型未返回 remaining_gap）')
            err_suffix = f"（执行期错误: {exec_error}）" if exec_error else ""

            # 📡 给 dashboard 用的细分字段（要在 _snapshot_state 调用前赋值）
            last_action_success = bool(success)
            last_reflection = reflection
            last_mission_complete = bool(mission_complete)
            last_mission_reason = mission_reason
            last_progress = (verification.get('progress') or "").strip()

            # subtasks_status: 模型返回完整 bool 数组（每步全量重报当前状态）
            # 用 historical OR 累积：true 一次永远 true，避免模型一不留神把 true 改回 false
            status = verification.get('subtasks_status')
            newly_done = []
            if isinstance(status, list) and len(status) == len(plan_state):
                for i, val in enumerate(status):
                    new_val = bool(val)
                    if new_val and not plan_state[i]:
                        plan_state[i] = True
                        newly_done.append(i)
            else:
                # 兼容旧字段 subtasks_done（增量索引数组），prompt 里没说但模型可能误返
                done_indices = verification.get('subtasks_done') or []
                for idx in done_indices:
                    if isinstance(idx, int) and 0 <= idx < len(plan_state) and not plan_state[idx]:
                        plan_state[idx] = True
                        newly_done.append(idx)
                if status is not None:
                    log(f"⚠️  subtasks_status 长度不匹配（期望 {len(plan_state)}，得到 {len(status) if isinstance(status, list) else type(status).__name__}），忽略")

            done_short = ", ".join([f"#{i+1}" for i in newly_done]) if newly_done else "无"
            progress_line = f"[{sum(plan_state)}/{len(plan)}]"
            last_verify_result = (
                f"上一步 [{act}] 作用于 [{target_label}]。"
                f"动作结果: {'成功' if success else '失败'}{err_suffix}（{reflection}）。"
                f"本步打勾: {done_short} {progress_line}。"
                f"任务整体: {'已完成' if mission_complete else '未完成'}（{mission_reason}）。"
                f"当前 Gap: {remaining}"
            )
            log(f"核验: action={'✓' if success else '✗'} {reflection}")
            log(f"      mission={'✓' if mission_complete else '✗'} {mission_reason}")
            log(f"      打勾: {done_short}  | 进度 {progress_line}")
            prog = (verification.get('progress') or "").strip()
            if prog and prog not in [plan[i] for i in newly_done]:
                pass  # progress 字段保留语义但不再单独追加列表（plan_state 是真相）

            # scratchpad 累积事实信息（去重 + 上限）
            new_notes = []
            for note in verification.get('notes_to_save', []) or []:
                if isinstance(note, str):
                    note = note.strip()
                    if note and note not in scratchpad:
                        scratchpad.append(note)
                        new_notes.append(note)
                        if len(scratchpad) > SCRATCHPAD_MAX:
                            scratchpad.pop(0)  # FIFO 淘汰最老的
            if new_notes:
                log(f"      📝 scratchpad +{len(new_notes)}: {' | '.join(new_notes)}")

            # 📡 #4 verify 后广播：plan_state 可能变了 + 新 reflection
            _output.send_state("", _snapshot_state())

            consecutive_fails = 0 if success else consecutive_fails + 1

            # --- 触发 finish gate：plan_state 全 True 或 mission_complete=true ---
            if all(plan_state) or mission_complete:
                trigger = "All subtasks [x]" if all(plan_state) else f"verify returned mission_complete=true ({mission_reason})"
                with profile("finish_gate"):
                    passed, ev = run_finish_gate(step, final_goal, plan, plan_state, scratchpad=scratchpad, trigger_reason=trigger)
                if passed:
                    log(f"✅ 目标自动确认达成！证据: {ev}")
                    run_status = f"SUCCESS ({trigger})"
                    break
                log(f"⚠️  finish 触发但 FINISH_CHECK 否决: {ev}")
                # 否决说明可能 plan 不够细 / 虚假打勾，回退最后一格让模型继续
                last_done = max((i for i, d in enumerate(plan_state) if d), default=-1)
                if last_done >= 0 and all(plan_state):
                    plan_state[last_done] = False
                    log(f"已回退最后一格: #{last_done+1} {plan[last_done]}，请模型继续推进")
                last_verify_result += f"\n[FINISH_CHECK 否决]: {ev}。请继续推进。"
                log(f"⚠️  verify 自报完成但 FINISH_CHECK 否决: {ev}")
                last_verify_result += f"\n[FINISH_CHECK 否决]: {ev}。请继续推进剩余 Gap，不要停。"
        else:
            last_verify_result = f"上一步 [{act}] 作用于 [{target_label}]，但核验调用未返回。执行期错误: {exec_error or '无'}"
            log("核验返回空")
            consecutive_fails += 1

        if consecutive_fails >= 3:
            log("⚠️  连续 3 步失败，触发兜底：home")
            get_device().home(); time.sleep(2)
            last_verify_result = "连续多步失败已触发兜底（已返回桌面），请重新规划，必要时 open_app 重启目标 app。"
            consecutive_fails = 0

        # Stuck-on-focus 检测：focus_idx 持续不动 → 多半 plan 不对路或路径走不通
        new_focus = next((i for i, d in enumerate(plan_state) if not d), -1)
        if new_focus == last_focus_idx and new_focus != -1:
            focus_stuck_count += 1
        else:
            focus_stuck_count = 0
        last_focus_idx = new_focus

        if focus_stuck_count >= FOCUS_STUCK_THRESHOLD:
            stuck_task = plan[new_focus] if 0 <= new_focus < len(plan) else "?"
            log(f"⚠️  Focus #{new_focus+1}「{stuck_task}」卡住 {focus_stuck_count} 步，触发 home 兜底")
            get_device().home(); time.sleep(2)
            last_verify_result = (
                f"⚠️ 焦点子任务 #{new_focus+1}「{stuck_task}」连续 {focus_stuck_count} 步未推进。"
                f"已触发 home 兜底回桌面。请重新评估：是路径不对、还是该 criterion 本就难以达成？"
                f"考虑换个动作策略 / 跳过该 criterion 直接推进下一项。"
            )
            focus_stuck_count = 0

        time.sleep(2)
    else:
        # for-else：循环正常跑完（没 break），说明 step 预算用尽
        log(f"⚠️  达到最大步数 ({steps_taken}) 仍未完成任务")

    # 跑完总结
    elapsed = int(time.time() - start_time)
    _print_run_summary(final_goal, plan, plan_state, scratchpad, steps_taken, run_status, elapsed)
    _overlay(f"{'✅' if 'SUCCESS' in run_status else '❌'} {run_status}\n{steps_taken} steps / {elapsed}s",
             snapshot=_snapshot_state())
    _print_phase_summary(wall_clock_sec=elapsed, n_steps=steps_taken)

if __name__ == "__main__":
    import sys
    goal_arg = " ".join(sys.argv[1:]).strip() or None
    main(goal_arg)
