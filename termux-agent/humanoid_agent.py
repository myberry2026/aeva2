"""
humanoid_agent_native_call.py — 使用 OpenAI Native Tool Calling 的 Android 自动化 Agent
对比 humanoid_agent.py（heuristic JSON 解析），验证原生 tool_calls 的可靠性。
"""
import time
import base64
import requests
import json
import os
import re
from datetime import datetime
from collections import defaultdict
from contextlib import contextmanager

# ws_channel: bridge 模式不需要（走 Bridge HTTP /events）; ADB 模式下用于接收用户输入（延迟 import）
from output_channel import create_output
from adb_utils import _adb_ensure_keyboard
from device_controller import ADBController, BridgeController
from bridge_client import BridgeClient

from tool_layer import (
    DECISION_TOOLS, REPORT_VERIFICATION_TOOL, TOOL_TO_ACTION,
    execute_tool_call, parse_tool_call_to_decision, parse_verification_tool_call,
    inventory_diff, format_inventory_diff, stitch_images, render_checklist,
)

# === 简单 profiling 工具 ===
_PHASE_TIMES = defaultdict(list)
_USAGE_BY_MODE = defaultdict(lambda: {"prompt": 0, "completion": 0, "calls": 0})

PHASE_TO_MODE = {
    "decision_llm": "DECISION",
    "verify_llm": "VERIFICATION",
    "finish_gate": "FINISH_CHECK",
}

def _record_usage(mode, usage):
    if not usage: return
    bucket = _USAGE_BY_MODE[mode]
    bucket["prompt"] += int(usage.get("prompt_tokens") or 0)
    bucket["completion"] += int(usage.get("completion_tokens") or 0)
    bucket["calls"] += 1

@contextmanager
def profile(name, verbose=True):
    t0 = time.time()
    try:
        yield
    finally:
        dt = time.time() - t0
        _PHASE_TIMES[name].append(dt)
        if verbose:
            print(f"    ⏱️  [{name}] {dt:.2f}s")

def _print_phase_summary(wall_clock_sec=None, n_steps=None):
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
    if wall_clock_sec is not None:
        dark = wall_clock_sec - grand_total
        dark_pct = (dark / wall_clock_sec * 100) if wall_clock_sec > 0 else 0
        per_step_dark = (dark / n_steps) if n_steps else 0
        print(f"   {'WALL CLOCK':18s} {wall_clock_sec:7.1f}s")
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
        "url": "http://100.113.214.52:1234/v1/chat/completions",  # "http://127.0.0.1:1234/v1/chat/completions",
        "model": "google/gemma-4-e4b"
        # "url": os.getenv("GALLERY_URL", "http://localhost:8080") + "/v1/chat/completions",
        # "model": "Gemma-4-E2B-it"
    },
}
CURRENT_MODEL = os.getenv("AGENT_MODEL", "GALLERY")

CONTROL_BACKEND = os.getenv("CONTROL_BACKEND", "bridge").lower()
assert CONTROL_BACKEND in ("adb", "bridge"), f"CONTROL_BACKEND must be adb/bridge, got {CONTROL_BACKEND!r}"

OUTPUT_TARGET = os.getenv("OUTPUT_TARGET", "overlay").lower()
assert OUTPUT_TARGET in ("overlay", "dashboard", "both"), f"OUTPUT_TARGET must be overlay/dashboard/both, got {OUTPUT_TARGET!r}"

BRIDGE_URL = os.getenv("BRIDGE_URL", "http://127.0.0.1:8765")
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "")
_hc = None

def get_bridge_client():
    global _hc
    if _hc is None:
        device = get_device()
        if hasattr(device, 'client'):
            _hc = device.client
        else:
            _hc = BridgeClient(BRIDGE_URL, BRIDGE_TOKEN)
    return _hc

VERIFY_STITCH = os.getenv("VERIFY_STITCH", "false").lower() == "true"
VERIFY_MODE = os.getenv("VERIFY_MODE", "both").lower()
assert VERIFY_MODE in ("xml", "images", "both"), f"VERIFY_MODE must be xml/images/both, got {VERIFY_MODE!r}"

RUN_DIR = "logs"
LOG_FILE = "logs/agent_debug.log"
RESP_FILE = "logs/agent_responses.log"
PLAN_CACHE_FILE = "logs/plan_cache.json"

def log(msg):
    print(f"[*] {msg}")

def save_debug_log(step, mode, prompt, response, usage=None, tool_calls=None, tool_result=None):
    raw_res = str(response) if response is not None else "<EMPTY RESPONSE>"
    formatted_response = raw_res
    try:
        if response and isinstance(response, str) and (response.strip().startswith('{') or response.strip().startswith('[')):
            data = json.loads(response)
            formatted_response = json.dumps(data, indent=2, ensure_ascii=False)
    except:
        pass

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        # 如果提供了 tool_result，说明是补充执行回执，不需要重新打一遍 PROMPT 和 RESPONSE
        if tool_result:
            f.write(f"[TOOL_RESULT]: {json.dumps(tool_result, ensure_ascii=False, default=str)}\n")
            return

        f.write(f"\n{'='*20} STEP {step} [{mode}] [{CURRENT_MODEL}] [NATIVE] {'='*20}\n")
        if usage:
            f.write(f"[USAGE]: {json.dumps(usage, ensure_ascii=False)}\n")
        if tool_calls:
            f.write(f"[TOOL_CALLS]: {json.dumps(tool_calls, ensure_ascii=False, default=str)}\n")
        f.write(f"[PROMPT]:\n{prompt}\n")
        f.write(f"\n[RESPONSE]:\n{formatted_response}\n")

    with open(RESP_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*20} STEP {step} [{mode}] [{CURRENT_MODEL}] [NATIVE] {'='*20}\n")
        if usage:
            f.write(f"[USAGE]: {json.dumps(usage)}\n")
        if tool_calls:
            f.write(f"[TOOL_CALLS]: {json.dumps(tool_calls, ensure_ascii=False, default=str)}\n")
        f.write(formatted_response + "\n")

    if usage:
        u_str = f"{usage.get('prompt_tokens','?')}/{usage.get('completion_tokens','?')}/{usage.get('total_tokens','?')}"
        log(f"[{mode}] Response received. Usage(in/out/total): {u_str}")
    else:
        log(f"[{mode}] Response received from {CURRENT_MODEL}.")
    if tool_calls:
        for tc in tool_calls:
            fn = tc.get("function", {})
            log(f"   🔧 Tool call: {fn.get('name')}({fn.get('arguments', '')[:100]})")
    if formatted_response and formatted_response != "<EMPTY RESPONSE>":
        print(formatted_response[:500] + ("..." if len(formatted_response) > 500 else ""))
    elif not tool_calls:
        log(f"⚠️  [{mode}] 收到空响应（无 tool_calls 也无 content）")

# --- 控制层 ---
SCREEN_W, SCREEN_H = 1080, 2400
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


# =============================================================================
# Native Tool Calling 版本的 agent_call
# =============================================================================

def agent_call_native(prompt, images, step, mode, tools=None, stitch=False):
    """
    通过 OpenAI 兼容接口调用模型，使用 native tool_calls。
    返回 (parsed_dict, raw_tool_calls) 或 (None, None)。
    """
    config = MODEL_OPTIONS[CURRENT_MODEL]
    url = config["url"]
    model_name = config["model"]

    if isinstance(images, str): images = [images]
    if stitch and len(images) > 1:
        stitched_path = f"{RUN_DIR}/_stitched_step_{step}_{mode}.png"
        stitch_images(images, stitched_path, axis="horizontal", label=True)
        images = [stitched_path]

    system_msg = {
        "role": "system",
        "content": (
            "You are a specialized Android automation robot. "
            "You MUST call tools to perform actions. Do NOT output preamble text. "
            "Every response MUST be a tool call. "
            "IMPORTANT: you should prioritize using a shortcut tool called teleport with apps (alarm, sms, map, call, email, search, calendar, etc.), "
            "it use Android Intent to jump there directly, which is much faster than clicking UI elements."
        )
    }
    user_content = []
    for p in images:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"}
            })
    user_content.append({"type": "text", "text": prompt})

    # 与 benchmark verify_native_toolcall.py 保持一致：只传 model/messages/tools/temperature
    payload = {
        "model": model_name,
        "messages": [
            system_msg,
            {"role": "user", "content": user_content}
        ],
        "stream": False,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 64,
        "max_tokens": 8192,
        "extra_body": {"enable_thinking": True},
    }
    if tools:
        payload["tools"] = tools

    payload_json = json.dumps(payload)
    log(f"   [LLM-NATIVE] 发送请求 ({mode})... Payload 大小: {len(payload_json)/1024:.1f} KB"
        + (f" | tools={len(tools)}" if tools else ""))

    t_start = time.time()
    raw_content = None
    raw_tool_calls = None
    usage = None

    try:
        r = requests.post(url, json=payload, timeout=int(os.getenv("LLM_TIMEOUT", "300")))
        dt = time.time() - t_start
        log(f"   [LLM-NATIVE] 收到响应! 耗时: {dt:.2f}s, 状态码: {r.status_code}")
        r.raise_for_status()
        res_json = r.json()

        msg = res_json['choices'][0]['message']
        raw_content = msg.get("content", "")
        reasoning = msg.get("reasoning_content") or msg.get("thought") or ""
        raw_tool_calls = msg.get("tool_calls")
        usage = res_json.get("usage")
        _record_usage(mode, usage)

        # 空响应时写原始 message JSON 到 debug log（不打 console）
        if not raw_tool_calls and (not raw_content or not raw_content.strip()):
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[EMPTY_RESPONSE_RAW]: {json.dumps(msg, ensure_ascii=False, default=str)}\n")

        save_debug_log(step, mode, prompt, raw_content, usage=usage, tool_calls=raw_tool_calls)

        # 优先使用 native tool_calls
        if raw_tool_calls:
            if mode == "VERIFICATION":
                parsed = parse_verification_tool_call(raw_tool_calls, n_plan=0)
            else:
                parsed = parse_tool_call_to_decision(raw_tool_calls)
            if parsed:
                return parsed, raw_tool_calls
            log(f"[{mode}] ⚠️ tool_calls 解析失败，回退到 content 解析")

        # Fallback: 从 content 或 reasoning 中解析 JSON
        parse_target = raw_content if raw_content else reasoning
        if parse_target:
            start = parse_target.find('{')
            if start >= 0:
                try:
                    obj, _end = json.JSONDecoder().raw_decode(parse_target[start:])
                    log(f"[{mode}] ⚠️ 使用了 content/reasoning fallback（非原生 tool_calls）")
                    if reasoning and not obj.get("thought"):
                        obj["thought"] = reasoning # 把思维链存进 thought 字段
                    return obj, None
                except json.JSONDecodeError:
                    match = re.search(r'\{.*?\}', parse_target, re.DOTALL)
                    if match:
                        try:
                            res = json.loads(match.group())
                            if reasoning and not res.get("thought"):
                                res["thought"] = reasoning
                            return res, None
                        except Exception:
                            pass

        log(f"[{mode}] ⚠️ 无法解析响应（无 tool_calls 且 content 解析失败）")
        return None, None

    except Exception as e:
        log(f"[{mode}] 调用失败: {e}")
        save_debug_log(step, mode, prompt, f"<ERROR> {e}\nRAW: {raw_content}", usage=usage, tool_calls=raw_tool_calls)
        return None, None


# =============================================================================
# Plan / Finish Gate（复用原逻辑，LLM 调用走 agent_call_native）
# =============================================================================

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
    """PLAN 阶段：纯文本 JSON 输出（不用 tool_calls，因为 plan 格式简单且模型稳定输出）。"""
    cached = get_plan_from_cache(final_goal)
    if cached:
        log("发现缓存的 PLAN，跳过 LLM 调用。")
        return cached

    prompt_plan = f"""你是一个 Android 自动化任务规划专家。

【总目标】: {final_goal}

请把总目标拆成【成功状态条件】清单（不是动作步骤！），满足：
1. 每条 ≤25 字，描述一个【可观察到的状态/结果】，而不是要做的动作
   ❌ 错："点击搜索按钮" / "进入详情页"（这是动作）
   ✅ 对："屏幕显示搜索结果列表" / "屏幕上看到了电话号码"（这是状态）
2. 每条必须可以通过单张截图肉眼判断 true/false
3. 状态条件 once-true-stays-true（达到过就视为完成，不会因为后续页面切换变 false）
4. 总数 1-5 条之间
5. 包含起始/收尾的状态条件

【严格禁令】:
- 严禁使用任何 LaTeX 符号（如 \\ge, \\le, \\times）。
- 严禁在 JSON 字符串中使用反斜杠 "\\"。
- 数学符号请用普通文本替代，如 ">= 4.6"。

返回 JSON（不要 markdown 包裹）:
{{"plan": ["状态条件1", "状态条件2", "..."]}}

⚠️ You MUST write all plan conditions in English.
"""
    # PLAN 不用 tool_calls，直接走 agent_call_native 但不传 tools
    res, _ = agent_call_native(prompt_plan, [], step, "PLAN")
    if not res: return None
    plan = res.get("plan")
    if not isinstance(plan, list) or not plan: return None
    cleaned = [str(s).strip() for s in plan if str(s).strip()][:8]
    if cleaned:
        save_plan_to_cache(final_goal, cleaned)
    return cleaned or None

def run_finish_gate(step, final_goal, plan, plan_state, scratchpad=None, trigger_reason=""):
    """二次核验门：截图 + checklist + scratchpad → 模型审计。"""
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
4. 如果有用户输入，以用户的判断为最高优先级，用户的最新要求可以覆盖原有要求，甚至提前结束任务。

返回 JSON:
{{ "truly_done": bool, "evidence": "≤60 words audit conclusion" }}

⚠️ You MUST reply in English.
"""
    check, _ = agent_call_native(check_prompt, pic_check, step, "FINISH_CHECK")
    if check and check.get('truly_done'):
        return True, check.get('evidence', '无')
    return False, (check.get('evidence', '核验未返回') if check else '核验调用失败')


def _print_run_summary(final_goal, plan, plan_state, scratchpad, steps_taken, status, elapsed_sec):
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


# =============================================================================
# Main Loop
# =============================================================================

def main(final_goal=None):
    global SCREEN_W, SCREEN_H, LOG_FILE, RESP_FILE, RUN_DIR
    print(">>> [DEBUG] Entering main() [NATIVE TOOL CALLING]...", flush=True)

    log(f"控制后端: {CONTROL_BACKEND}")
    log(f"🔧 模式: NATIVE TOOL CALLING (vs 原版 heuristic JSON)")
    if CONTROL_BACKEND == "bridge":
        hc = get_bridge_client()
        if not hc.is_ready():
            log("⚠️  bridge 未就绪，请确认 bridge-android app 已启动且 AX service 已开启")
            log(f"   尝试连接: {BRIDGE_URL}")
        else:
            log(f"✅ bridge 已连接: {BRIDGE_URL}")
    else:
        _adb_ensure_keyboard()

    m_cfg = MODEL_OPTIONS.get(CURRENT_MODEL, {})
    m_url = m_cfg.get("url", "")
    log(f"模型后端: {CURRENT_MODEL} ({m_url})")
    try:
        health_url = m_url.replace("/v1/chat/completions", "/health")
        r = requests.get(health_url, timeout=3)
        if r.status_code == 200:
            log(f"✅ 模型服务器已就绪: {r.json().get('status', 'ok')}")
        else:
            log(f"⚠️  模型服务器响应异常: {r.status_code}")
    except Exception as e:
        log(f"⚠️  无法连接模型服务器: {e}")

    _bc = get_bridge_client() if CONTROL_BACKEND == "bridge" else None
    _output = create_output(OUTPUT_TARGET, bridge_client=_bc,
                            ws_port=int(os.getenv("WS_PORT", "8768")))
    _output.start()
    _output.reset()

    def _overlay(text, snapshot=None):
        try:
            _output.send_state(text, snapshot or {})
        except Exception:
            pass

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    RUN_DIR = f"logs/run_{timestamp}_native"
    os.makedirs(RUN_DIR, exist_ok=True)
    LOG_FILE = f"{RUN_DIR}/agent_debug.log"
    RESP_FILE = f"{RUN_DIR}/agent_responses.log"

    if final_goal is None:
        final_goal = "在地图搜索 'best pizza in San Francisco'，滚动寻找一家评分 >= 4.6 的店点进去，拿到电话号码，最后退回地图主页。"
    log("=== 启动【Native Tool Calling 版】Agent ===")
    log(f"目标: {final_goal}")
    SCREEN_W, SCREEN_H = get_device().get_screen_size()
    log(f"屏幕尺寸: {SCREEN_W}x{SCREEN_H}")

    installed_apps = get_device().get_installed_apps()
    log(f"已发现 {len(installed_apps)} 个 launcher app（prefetch）")
    apps_str = ", ".join(installed_apps) if installed_apps else "(prefetch 失败)"

    # === 初始化状态 (为早期发送 dashboard state 做准备) ===
    plan = []
    plan_state = []
    last_verify_result = "Task started. Check screen and navigate if needed."
    consecutive_fails = 0
    scratchpad = []
    SCRATCHPAD_MAX = 20

    last_focus_idx = -2
    focus_stuck_count = 0
    FOCUS_STUCK_THRESHOLD = 4

    run_status = "STARTING"
    steps_taken = 0
    start_time = time.time()

    last_thought = ""
    current_target = ""
    last_action_success = None
    last_reflection = ""
    last_mission_complete = None
    last_mission_reason = ""
    last_progress = ""

    # Native-specific 统计
    native_toolcall_count = 0
    fallback_count = 0

    def _snapshot_state():
        prof_total = sum(sum(v) for v in _PHASE_TIMES.values()) if '_PHASE_TIMES' in globals() else 0
        llm_total = sum(sum(v) for k, v in _PHASE_TIMES.items() if k.endswith("_llm") or k == "finish_gate") if '_PHASE_TIMES' in globals() else 0
        in_tok = sum(u["prompt"] for u in _USAGE_BY_MODE.values()) if '_USAGE_BY_MODE' in globals() else 0
        out_tok = sum(u["completion"] for u in _USAGE_BY_MODE.values()) if '_USAGE_BY_MODE' in globals() else 0
        focus = next((i for i, d in enumerate(plan_state) if not d), -1)
        return {
            "type": "state",
            "goal": final_goal,
            "step": steps_taken,
            "max_steps": 15,
            "status": run_status,
            "elapsed": int(time.time() - start_time),
            "model": CURRENT_MODEL,
            "mode": "NATIVE_TOOLCALL",
            "plan": plan,
            "plan_state": list(plan_state),
            "focus_idx": focus,
            "scratchpad": list(scratchpad),
            "last_thought": last_thought,
            "last_verify": last_verify_result[:400],
            "current_target": current_target,
            "last_action_success": last_action_success,
            "last_reflection": last_reflection,
            "last_mission_complete": last_mission_complete,
            "last_mission_reason": last_mission_reason,
            "last_progress": last_progress,
            "native_stats": {
                "toolcall_count": native_toolcall_count,
                "fallback_count": fallback_count,
                "toolcall_rate": f"{native_toolcall_count/(native_toolcall_count+fallback_count)*100:.0f}%" if (native_toolcall_count+fallback_count) > 0 else "N/A",
            },
            "profile": {
                "wall": int(time.time() - start_time),
                "profiled": round(prof_total, 1),
                "llm": round(llm_total, 1),
                "in_tok": in_tok,
                "out_tok": out_tok,
            },
        }

    # 📡 接收到目标后立刻发 overlay（dashboard 初始化）
    _overlay(f"⏳ Thinking...\n🎯 {final_goal}", snapshot=_snapshot_state())
    _output.send_state("", _snapshot_state())

    log("=== PLAN 阶段：拆解任务 ===")
    with profile("plan_llm"):
        plan = plan_call(final_goal)
    if not plan:
        log("⚠️  PLAN 调用失败，退化为单项 plan")
        plan = [final_goal]
    plan_state = [False] * len(plan)
    log("任务拆解完成：")
    for i, t in enumerate(plan):
        log(f"  {i+1}. {t}")

    # 📡 Plan 出来后再发一次 overlay 更新计划
    _overlay(f"📋 {final_goal}\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(plan)),
             snapshot=_snapshot_state())
    _output.send_state("", _snapshot_state())

    last_event_timestamp = int(time.time() * 1000)

    # Force return to home screen before starting the first step
    log("🏠 Forcing back to home screen before starting task...")
    get_device().home()
    time.sleep(2)

    for step in range(1, 16):
        steps_taken = step

        # 1) 用户插话
        user_text = None
        source = None

        if CONTROL_BACKEND == "bridge":
            # Bridge 模式：通过 Bridge HTTP /events 轮询语音事件
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
        else:
            # ADB 模式：通过 ws_channel 接收用户输入（ws_client_cli / dashboard）
            try:
                from ws_channel import ws_poll
                ws_msg = ws_poll()
                if ws_msg:
                    user_text = ws_msg.get("text") or ws_msg.get("msg") or json.dumps(ws_msg, ensure_ascii=False)
                    source = "WS"
            except ImportError:
                pass

        if user_text:
            log(f"\n{'🎤'*20}")
            log(f"🎤 USER (via {source}) @ step {step}: {user_text}")
            log(f"{'🎤'*20}\n")
            scratchpad.append(f"[⚠️ USER 插话 ({source}) @ step {step}] {user_text}")
            last_verify_result = (
                f"⚠️⚠️⚠️ 用户刚刚 ({source}) 插话：「{user_text}」\n"
                f"请优先响应用户指令，如果有用户输入，以用户的判断为最高优先级，用户的最新要求可以覆盖原有要求——比如对应 criterion 不可观测但用户授权了，"
                f"把对应 subtasks_status 设 true 或直接 action='finish'。\n\n"
                f"上一步原本反馈：{last_verify_result}"
            )
            _output.send_event({"type": "event", "kind": "user_input", "text": user_text, "step": step})
            _output.send_state("", _snapshot_state())

        # 2) 截图 + UI inventory
        pic_before = f"{RUN_DIR}/step_{step}_before.png"
        with profile("screenshot_before"):
            get_device().take_screenshot(pic_before)
        with profile("ui_dump"):
            elements = get_device().get_inventory()
        # 精简 UI 树：过滤掉既没有文字也没有描述的元素，节省 Token
        filtered_elements = [e for e in elements if (e.get('label') and e.get('label').strip())]
        if not filtered_elements: # 兜底：如果过滤完没了，就用原版的
            filtered_elements = elements
        list_str = "\n".join([f"ID {e['id']}: '{e['label'][:50]}'... @ {e['pos']}" if len(e['label']) > 50 else f"ID {e['id']}: '{e['label']}' @ {e['pos']}" for e in filtered_elements])
        focus_idx = next((idx for idx, d in enumerate(plan_state) if not d), -1)
        checklist = render_checklist(plan, plan_state, focus_idx)
        focus_task = plan[focus_idx] if focus_idx >= 0 else "（全部已完成）"

        log(f"\n--- 第 {step} 步：决策阶段 [{sum(plan_state)}/{len(plan)}] [NATIVE] ---")
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
1. 当前截图处于哪个 app / 页面？是否已经在目标 app？没有的话先 open_app 或者直接使用 teleport to 对应 app。
2. 刚才那一步生效了吗？没生效的根因是什么？
3. 离总目标还差什么？**请对比【总目标】与【已达成成就】，严禁重复执行已完成的步骤。**
4. 如果目标已达成，请果断调用 android_finish，不要因为页面细节微差而尝试重新开始。
5. 优先用 id；只有当目标元素在清单中确实找不到时，才改用 point 坐标。

你必须调用工具来执行动作。不要输出纯文字。

⚠️ You MUST write your 'thought' field in English.
"""
        with profile("decision_llm"):
            decision, raw_tc = agent_call_native(
                prompt_decide, pic_before, step, "DECISION",
                tools=DECISION_TOOLS
            )

        # 统计 native vs fallback
        if raw_tc:
            native_toolcall_count += 1
        elif decision:
            fallback_count += 1

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

        print("\n" + ">"*10 + " AI 深度 Gap 分析 [NATIVE] " + "<"*10)
        print(decision.get('thought', '分析中...'))
        print(">"*35 + "\n")

        last_thought = (decision.get('thought') or "").strip()

        if CONTROL_BACKEND == "bridge" and last_thought:
            try:
                get_bridge_client().send_chat_message("agent", last_thought, is_markdown=True)
            except Exception as e:
                log(f"⚠️ Error sending thought to Chat UI: {e}")
            _overlay(f"🎯 {final_goal}\n" + "-"*15 + "\n" + checklist + f"\n\n🤔 思考: {last_thought}",
                     snapshot=_snapshot_state())

        _act = decision.get('action', '?')
        _id = decision.get('id')
        _pt = decision.get('point')
        _txt = decision.get('text')
        _parts = [f"{_act}"]
        if _id is not None: _parts.append(f"id={_id}")
        if _pt: _parts.append(f"pt={_pt}")
        if _txt: _parts.append(f'text="{_txt[:30]}"')
        current_target = " ".join(_parts)

        # === 执行动作（通过 tool_layer） ===
        if raw_tc:
            # Native path: 直接从 tool_calls 执行
            tc = raw_tc[0]
            tool_name = tc["function"]["name"]
            try:
                tool_args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
            except json.JSONDecodeError:
                tool_args = {}

            log(f"[*] 执行 native tool call: {tool_name}")
            result = execute_tool_call(tool_name, tool_args, get_device(), elements, SCREEN_W, SCREEN_H, installed_apps)
            save_debug_log(step, "DECISION", prompt_decide, None, tool_result=result)
            exec_error = result["error"]
            target_label = result["target_label"]
            finish_requested = result["finish_requested"]
            act = result["action"]
        else:
            # Fallback path: 从 parsed decision dict 执行（模拟原版逻辑）
            act = decision.get("action")
            target_label = "N/A"
            exec_error = None
            finish_requested = False

            try:
                # 注入 _action 供 resolve_target 用
                decision["_action"] = act
                from tool_layer import resolve_target
                target_pos, target_label = resolve_target(decision, elements, SCREEN_W, SCREEN_H)
                log(f"[*] 执行 fallback 动作: {act} (目标: {target_label})")
                if act == "click": get_device().tap(*target_pos)
                elif act == "type": get_device().tap_and_type(target_pos[0], target_pos[1], decision.get('text', ''), editor_action=decision.get('editor_action'))
                elif act == "long_press": get_device().long_press(*target_pos)
                elif act == "scroll_down": get_device().swipe(SCREEN_W//2, SCREEN_H*3//4, SCREEN_W//2, SCREEN_H//4)
                elif act == "scroll_up": get_device().swipe(SCREEN_W//2, SCREEN_H//4, SCREEN_W//2, SCREEN_H*3//4)
                elif act == "back": get_device().back()
                elif act == "home": get_device().home()
                elif act == "teleport":
                    get_device().go_to(decision.get('task'), decision.get('query'))
                elif act == "open_app":
                    pkg = decision.get('pkg')
                    if not pkg:
                        exec_error = "open_app 缺少 pkg 字段"
                    else:
                        get_device().open_app(pkg)
                elif act == "wait": adb_wait(decision.get('seconds', 3))
                elif act == "finish": finish_requested = True
                else: exec_error = f"未知动作: {act!r}"

                # Fallback 也模拟一个 result 存进 log
                result_fallback = {"action": act, "target_label": target_label, "error": exec_error, "finish_requested": finish_requested}
                save_debug_log(step, "DECISION", prompt_decide, None, tool_result=result_fallback)

            except (IndexError, KeyError, TypeError, ValueError) as e:
                exec_error = f"{type(e).__name__}: {e}"
                log(f"执行出错: {exec_error}")
                save_debug_log(step, "DECISION", prompt_decide, None, tool_result={"error": exec_error})

        log(f"[*] 动作指令 {act} 已发出")

        # --- finish 二次核验门 ---
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

        # --- 核验步 ---
        time.sleep(4)
        log(f"--- 第 {step} 步：结果核验（模式={VERIFY_MODE}）[NATIVE] ---")
        pic_after = f"{RUN_DIR}/step_{step}_after.png"

        with profile("screenshot_after"):
            get_device().take_screenshot(pic_after)

        elements_diff_text = ""
        if VERIFY_MODE in ("xml", "both"):
            with profile("ui_dump_after"):
                elements_after = get_device().get_inventory()
            diff = inventory_diff(elements, elements_after)
            elements_diff_text = format_inventory_diff(diff)
            log(f"      🔍 UI diff: 新出现 {len(diff['appeared'])}, 消失 {len(diff['disappeared'])}")

        if VERIFY_MODE == "xml":
            img_desc = "本次核验【纯 XML 模式】：没有截图，只看 UI 元素的程序级变化判断。"
            verify_images = []
        elif VERIFY_STITCH:
            img_desc = "我会传一张拼接图给你：左半边是【动作前 BEFORE】，右半边是【动作后 AFTER】。"
            verify_images = [pic_before, pic_after]
        else:
            img_desc = "我会传两张图给你：第一张是【动作前 BEFORE】，第二张是【动作后 AFTER】。"
            verify_images = [pic_before, pic_after]

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

⚠️ 字段规则：
- action_success vs mission_complete 是两件事
- progress：单个字符串。这一步带来的真实进展，无则填空字符串
- remaining_gap：只写还没做的具体下一步动作，mission_complete 时填 None
- notes_to_save：具体事实/数字/名字/地址，每条≤30字且自带 context，没有填 []

你必须【且仅能】调用 report_verification 工具来报告结果。
⚠️ 严禁在此阶段尝试调用 click, type 或任何其他操作类工具！你现在的身份是核验员。
⚠️ You MUST write all text fields (reflection, progress, mission_reason, remaining_gap, notes_to_save) in English.
"""
        with profile("verify_llm"):
            do_stitch = VERIFY_STITCH and len(verify_images) > 1
            verification, raw_tc_v = agent_call_native(
                prompt_verify, verify_images, step, "VERIFICATION",
                tools=[REPORT_VERIFICATION_TOOL],
                stitch=do_stitch
            )
            if raw_tc_v:
                native_toolcall_count += 1
            elif verification:
                fallback_count += 1

        if verification:
            success = verification.get('action_success', False)
            mission_complete = verification.get('mission_complete', False)
            reflection = verification.get('reflection', '（模型未返回 reflection）')
            mission_reason = verification.get('mission_reason', '（模型未返回 mission_reason）')
            _overlay(f"{'✓' if success else '✗'} {act} → {reflection[:50]}",
                     snapshot=_snapshot_state())
            remaining = verification.get('remaining_gap', '（模型未返回 remaining_gap）')
            err_suffix = f"（执行期错误: {exec_error}）" if exec_error else ""

            last_action_success = bool(success)
            last_reflection = reflection
            last_mission_complete = bool(mission_complete)
            last_mission_reason = mission_reason
            last_progress = (verification.get('progress') or "").strip()

            status = verification.get('subtasks_status')
            newly_done = []
            if isinstance(status, list) and len(status) == len(plan_state):
                for i, val in enumerate(status):
                    new_val = bool(val)
                    if new_val and not plan_state[i]:
                        plan_state[i] = True
                        newly_done.append(i)
            else:
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

            new_notes = []
            for note in verification.get('notes_to_save', []) or []:
                if isinstance(note, str):
                    note = note.strip()
                    if note and note not in scratchpad:
                        scratchpad.append(note)
                        new_notes.append(note)
                        if len(scratchpad) > SCRATCHPAD_MAX:
                            scratchpad.pop(0)
            if new_notes:
                log(f"      📝 scratchpad +{len(new_notes)}: {' | '.join(new_notes)}")

            _output.send_state("", _snapshot_state())
            consecutive_fails = 0 if success else consecutive_fails + 1

            if all(plan_state) or mission_complete:
                trigger = "All subtasks [x]" if all(plan_state) else f"verify returned mission_complete=true ({mission_reason})"
                with profile("finish_gate"):
                    passed, ev = run_finish_gate(step, final_goal, plan, plan_state, scratchpad=scratchpad, trigger_reason=trigger)
                if passed:
                    log(f"✅ 目标自动确认达成！证据: {ev}")
                    run_status = f"SUCCESS ({trigger})"
                    break
                log(f"⚠️  finish 触发但 FINISH_CHECK 否决: {ev}")
                last_done = max((i for i, d in enumerate(plan_state) if d), default=-1)
                if last_done >= 0 and all(plan_state):
                    plan_state[last_done] = False
                    log(f"已回退最后一格: #{last_done+1} {plan[last_done]}，请模型继续推进")
                last_verify_result += f"\n[FINISH_CHECK 否决]: {ev}。请继续推进。"
        else:
            last_verify_result = f"上一步 [{act}] 作用于 [{target_label}]，但核验调用未返回。执行期错误: {exec_error or '无'}"
            log("核验返回空")
            consecutive_fails += 1

        if consecutive_fails >= 3:
            log("⚠️  连续 3 步失败，触发兜底：home")
            get_device().home(); time.sleep(2)
            last_verify_result = "连续多步失败已触发兜底（已返回桌面），请重新规划，必要时 open_app 重启目标 app。"
            consecutive_fails = 0

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
            )
            focus_stuck_count = 0

        time.sleep(2)
    else:
        run_status = "STEPS_EXHAUSTED"
        log(f"⚠️  达到最大步数 ({steps_taken}) 仍未完成任务")

    elapsed = int(time.time() - start_time)
    _print_run_summary(final_goal, plan, plan_state, scratchpad, steps_taken, run_status, elapsed)
    _overlay(f"{'✅' if 'SUCCESS' in run_status else '❌'} {run_status}\n{steps_taken} steps / {elapsed}s",
             snapshot=_snapshot_state())
    _print_phase_summary(wall_clock_sec=elapsed, n_steps=steps_taken)

    # === Native 统计汇总 ===
    total_calls = native_toolcall_count + fallback_count
    print("\n" + "=" * 60)
    print("  🔧 Native Tool Calling 统计")
    print("=" * 60)
    print(f"  原生 tool_calls: {native_toolcall_count}/{total_calls} ({native_toolcall_count/total_calls*100:.0f}%)" if total_calls else "  无 LLM 调用")
    print(f"  Fallback (content parse): {fallback_count}/{total_calls}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    import sys
    goal_arg = " ".join(sys.argv[1:]).strip() or None
    main(goal_arg)
