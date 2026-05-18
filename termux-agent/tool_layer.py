import time
import inspect
import json
import re
import types
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints, Callable
from PIL import Image, ImageDraw

# === Standalone get_json_schema implementation (extracted from transformers) ===
description_re = re.compile(r"^(.*?)[\n\s]*(Args:|Returns:|Raises:|\Z)", re.DOTALL)
args_re = re.compile(r"\n\s*Args:\n\s*(.*?)[\n\s]*(Returns:|Raises:|\Z)", re.DOTALL)
args_split_re = re.compile(r"(?:^|\n)\s*(\w+):\s*(.*?)\s*(?=\n\s*\w+:|\Z)", re.DOTALL | re.VERBOSE)

def _get_json_schema_type(param_type: type) -> dict[str, str]:
    type_mapping = {int: {"type": "integer"}, float: {"type": "number"}, str: {"type": "string"},
                    bool: {"type": "boolean"}, type(None): {"type": "null"}, Any: {}}
    return type_mapping.get(param_type, {"type": "object"})

def _parse_type_hint(hint: Any) -> dict:
    origin, args = get_origin(hint), get_args(hint)
    if origin is None: return _get_json_schema_type(hint)
    elif origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType):
        subtypes = [_parse_type_hint(t) for t in args if t is not type(None)]
        res = subtypes[0] if len(subtypes) == 1 else ({"type": sorted([s["type"] for s in subtypes])} if all("type" in s and isinstance(s["type"], str) for s in subtypes) else {"anyOf": subtypes})
        if type(None) in args: res["nullable"] = True
        return res
    elif origin is Literal and len(args) > 0:
        return {"type": _get_json_schema_type(type(args[0])).get("type"), "enum": list(args)}
    elif origin is list:
        return {"type": "array", "items": _parse_type_hint(args[0])} if args else {"type": "array"}
    elif origin is dict:
        return {"type": "object", "additionalProperties": _parse_type_hint(args[1])} if len(args) == 2 else {"type": "object"}
    return {"type": "object"}

def get_json_schema(func: Callable) -> dict:
    doc = inspect.getdoc(func) or ""
    main_doc = description_re.search(doc).group(1).strip() if description_re.search(doc) else ""
    args_match = args_re.search(doc)
    args_dict = {m[0]: re.sub(r"\s*\n+\s*", " ", m[1].strip()) for m in args_split_re.findall(args_match.group(1).strip())} if args_match else {}
    
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    props, req = {}, []
    for name, param in sig.parameters.items():
        if name in ("self", "cls"): continue
        props[name] = _parse_type_hint(hints.get(name, type(param.default) if param.default != inspect.Parameter.empty else str))
        props[name]["description"] = args_dict.get(name, "")
        if param.default == inspect.Parameter.empty: req.append(name)
    
    return {"type": "function", "function": {"name": getattr(func, "__name__", "op"), "description": main_doc, "parameters": {"type": "object", "properties": props, "required": req}}}

def _fix_array_types(schema):
    """
    OpenAI 兼容接口要求 array 必须带 items。
    """
    if "function" in schema and "parameters" in schema["function"]:
        props = schema["function"]["parameters"].get("properties", {})
        for name, prop in props.items():
            if name == "point":
                prop["type"] = "array"
                prop["items"] = {"type": "integer"}
            elif name == "subtasks_status":
                prop["type"] = "array"
                prop["items"] = {"type": "boolean"}
            elif name == "notes_to_save":
                prop["type"] = "array"
                prop["items"] = {"type": "string"}
            elif prop.get("type") == "object" and name in ("point", "subtasks_status", "notes_to_save"):
                # 兜底：如果 transformers 给成了 object，强行纠正
                prop["type"] = "array"
                prop["items"] = {"type": "string"} # 默认 string
    return schema

def _make_schema(fn):
    schema = get_json_schema(fn)
    # 移除 android_ 前缀
    if "function" in schema:
        name = schema["function"]["name"]
        if name.startswith("android_"):
            name = name.replace("android_", "")
        if name == "type_text":
            name = "type"
        schema["function"]["name"] = name
    return _fix_array_types(schema)


# =============================================================================
# 1. Tool Functions (docstring + signature = schema source)
# =============================================================================

def click(thought: str, id: int = None, point: list = None):
    """
    点击屏幕上的某个元素。优先用 id（清单里的索引），找不到时用 point 坐标。

    Args:
        thought: 分析：当前页面状态、为什么点这个目标、预期效果
        id: 可交互清单中的元素索引（优先使用）
        point: 备用坐标 [x, y]，仅当清单找不到目标时使用
    """
    pass

def type_text(thought: str, text: str, id: int = None, point: list = None, editor_action: str = None):
    """
    在输入框中输入文本。先点击目标输入框（用 id 或 point），再输入。

    Args:
        thought: 分析：当前状态、要输入什么、为什么
        text: 要输入的文本内容
        id: 输入框在清单中的索引
        point: 备用坐标 [x, y]
        editor_action: 输入后的 editor action。搜索框填 search，消息发送填 send，普通文本框不填。可选值: search, send, done, go, next, previous
    """
    pass

def long_press(thought: str, id: int = None, point: list = None):
    """
    长按屏幕上的某个元素。

    Args:
        thought: 分析：为什么需要长按
        id: 目标元素在清单中的索引
        point: 备用坐标 [x, y]
    """
    pass

def scroll_down(thought: str):
    """
    向下滚动屏幕，查看更多内容。

    Args:
        thought: 分析：为什么需要向下滚、在找什么
    """
    pass

def scroll_up(thought: str):
    """
    向上滚动屏幕。

    Args:
        thought: 分析：为什么需要向上滚
    """
    pass

def back(thought: str):
    """
    按系统返回键。

    Args:
        thought: 分析：为什么要返回
    """
    pass

def home(thought: str):
    """
    按 Home 键回到桌面。

    Args:
        thought: 分析：为什么要回桌面
    """
    pass

def teleport(thought: str, task: str, query: str = None):
    """
    语义化瞬间移动。直接跳转到特定功能或应用页面，无需手动导航。
    极力推荐：当你需要发短信、定闹钟、查地图、搜索、查看推特/Reddit、或进入系统设置时，直接使用此工具。

    Args:
        thought: 理由：为什么要执行这次跳转
        task: 任务关键字。支持：
            - map: 地图搜索 (query 填地点)
            - route: 路径规划 (query 填 {'origin': '...', 'destination': '...'})
            - sms: 发短信 (query 填号码)
            - call: 拨号盘 (query 填号码)
            - email: 发邮件 (query 填地址)
            - search: Google 搜索 (query 填关键词)
            - youtube/twitter/reddit: 第三方 App (query 填 ID 或关键词)
            - alarm: 定闹钟 (query 填 {'hour': 8, 'minutes': 30, 'message': '...'})
            - calendar: 插日历 (query 填 {'title': '...', 'description': '...'})
            - wifi/bt/battery/settings: 系统设置
        query: 目标参数。可以是字符串（如 '10086'）或字典（如 {'hour': 8}）。
    """
    pass

def open_app(thought: str, pkg: str):
    """
    打开指定应用。pkg 必须是已安装应用的包名。

    Args:
        thought: 分析：为什么要打开这个 app
        pkg: 应用包名，如 com.google.android.gm
    """
    pass

def wait(thought: str, seconds: int = 3):
    """
    等待指定秒数，用于等待页面加载或动画完成。

    Args:
        thought: 分析：为什么要等待
        seconds: 等待秒数，默认 3
    """
    pass

def finish(thought: str):
    """
    声明任务已完成。会触发二次核验门确认。

    Args:
        thought: 分析：为什么认为任务已全部完成
    """
    pass

def report_verification(
    action_success: bool,
    reflection: str,
    progress: str,
    remaining_gap: str,
    mission_complete: bool,
    mission_reason: str,
    subtasks_status: list,
    notes_to_save: list,
):
    """
    报告动作执行后的验证结果。

    Args:
        action_success: 这一步动作是否生效，界面是否朝目标方向变化了
        reflection: ≤40字，解释 action_success 的判断理由
        progress: ≤30字，这一步的真实进展，无则填空字符串
        remaining_gap: 还差什么具体动作，mission_complete 时填 None
        mission_complete: 整个总目标是否全部完成
        mission_reason: ≤40字，解释 mission_complete 的判断理由
        subtasks_status: 与任务清单一一对应的 boolean 数组，once-true-stays-true
        notes_to_save: 这步看到的具体事实/数字/名字/地址，每条≤30字且自带 context
    """
    pass


# =============================================================================
# 2. Schema 生成（get_json_schema + 手动修复 list→array）
# =============================================================================

def _fix_array_types(schema):
    """get_json_schema 把 list 参数变成 'object'，手动修回 'array'。"""
    props = schema.get("function", {}).get("parameters", {}).get("properties", {})
    for name, prop in props.items():
        if prop.get("type") == "object" and name in ("point", "subtasks_status", "notes_to_save"):
            if name == "point":
                prop["type"] = "array"
                prop["items"] = {"type": "integer"}
            elif name == "subtasks_status":
                prop["type"] = "array"
                prop["items"] = {"type": "boolean"}
            elif name == "notes_to_save":
                prop["type"] = "array"
                prop["items"] = {"type": "string"}
    return schema

# 自动从函数签名 + docstring 生成 OpenAI tools 格式
DECISION_TOOLS = [
    _make_schema(click),
    _make_schema(type_text),
    _make_schema(long_press),
    _make_schema(scroll_down),
    _make_schema(scroll_up),
    _make_schema(teleport),
    _make_schema(back),
    _make_schema(home),
    _make_schema(open_app),
    _make_schema(wait),
    _make_schema(finish),
]

REPORT_VERIFICATION_TOOL = _make_schema(report_verification)

# Tool name (model perspective) → internal action name
TOOL_TO_ACTION = {
    "click": "click",
    "type": "type",
    "long_press": "long_press",
    "scroll_down": "scroll_down",
    "scroll_up": "scroll_up",
    "teleport": "teleport",
    "back": "back",
    "home": "home",
    "open_app": "open_app",
    "wait": "wait",
    "finish": "finish",
}


# =============================================================================
# 3. Tool Execution
# =============================================================================

def resolve_target(args, elements, screen_w, screen_h):
    """
    从 tool call 参数中解析点击目标。
    优先 id → 兜底 point → 全局动作返回 None。
    """
    i = args.get("id")
    if isinstance(i, int) and 0 <= i < len(elements):
        e = elements[i]
        return e["pos"], e["label"]

    p = args.get("point")
    if isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p):
        clamped = [
            max(0, min(screen_w - 1, int(p[0]))),
            max(0, min(screen_h - 1, int(p[1]))),
        ]
        return clamped, f"坐标点 {clamped}"

    action = args.get("_action", "")
    if action in ("scroll_down", "scroll_up", "back", "home", "open_app", "wait", "finish", "teleport"):
        return None, "系统/全局"

    if i is None:
        raise ValueError(
            "该动作要求提供 ID，但你返回了 id: null（也未提供 point 备选）。"
            "请在【当前可交互清单】中准确寻找目标元素的 ID；"
            "若清单里确实没有，请在 point 字段给出截图估算的坐标。"
        )
    raise IndexError(f"id={i!r} 越界（清单仅 {len(elements)} 项）")


def execute_tool_call(tool_name, arguments, device, elements, screen_w, screen_h, installed_apps=None):
    """
    执行一个 native tool call。
    返回 {"success": bool, "target_label": str, "error": str|None, "action": str, "finish_requested": bool}
    """
    action = TOOL_TO_ACTION.get(tool_name)
    if not action:
        return {"success": False, "target_label": "N/A", "error": f"未知工具: {tool_name}", "action": tool_name, "finish_requested": False}

    arguments["_action"] = action
    exec_error = None
    target_label = "N/A"
    finish_requested = False

    try:
        target_pos, target_label = resolve_target(arguments, elements, screen_w, screen_h)

        if action == "click":
            device.tap(*target_pos)
        elif action == "type":
            device.tap_and_type(
                target_pos[0], target_pos[1],
                arguments.get("text", ""),
                editor_action=arguments.get("editor_action")
            )
        elif action == "long_press":
            device.long_press(*target_pos)
        elif action == "scroll_down":
            device.scroll_down()
        elif action == "scroll_up":
            device.scroll_up()
        elif action == "teleport":
            device.go_to(arguments.get("task"), arguments.get("query"))
        elif action == "back":
            device.back()
        elif action == "home":
            device.home()
        elif action == "open_app":
            pkg = arguments.get("pkg")
            if not pkg:
                exec_error = "open_app 缺少 pkg 字段"
            else:
                if installed_apps and pkg not in installed_apps:
                    pass
                device.open_app(pkg)
        elif action == "wait":
            import time
            time.sleep(arguments.get("seconds", 3))
        elif action == "finish":
            finish_requested = True
        else:
            exec_error = f"未知动作: {action!r}"

    except (IndexError, KeyError, TypeError, ValueError) as e:
        exec_error = f"{type(e).__name__}: {e}"

    return {
        "success": exec_error is None,
        "target_label": target_label,
        "error": exec_error,
        "action": action,
        "finish_requested": finish_requested,
    }


def parse_tool_call_to_decision(tool_calls):
    """
    把 native tool_calls 响应转换为和 heuristic JSON 相同格式的 decision dict。
    """
    if not tool_calls:
        return None

    tc = tool_calls[0]
    func = tc.get("function", {})
    name = func.get("name", "")
    args_str = func.get("arguments", "{}")

    try:
        args = json.loads(args_str) if isinstance(args_str, str) else args_str
    except json.JSONDecodeError:
        args = {}

    action = TOOL_TO_ACTION.get(name)
    if not action:
        return None

    decision = {
        "thought": args.get("thought", ""),
        "action": action,
    }
    if "id" in args:
        decision["id"] = args["id"]
    if "point" in args:
        decision["point"] = args["point"]
    if "text" in args:
        decision["text"] = args["text"]
    if "editor_action" in args:
        decision["editor_action"] = args["editor_action"]
    if "pkg" in args:
        decision["pkg"] = args["pkg"]
    if "seconds" in args:
        decision["seconds"] = args["seconds"]

    return decision


def parse_verification_tool_call(tool_calls, n_plan):
    """
    把 verification tool_calls 响应转换为和 heuristic JSON 相同格式的 dict。
    """
    if not tool_calls:
        return None

    tc = tool_calls[0]
    func = tc.get("function", {})
    name = func.get("name", "")
    args_str = func.get("arguments", "{}")

    try:
        args = json.loads(args_str) if isinstance(args_str, str) else args_str
    except json.JSONDecodeError:
        return None

    if name != "report_verification":
        return None

    return {
        "action_success": args.get("action_success", False),
        "reflection": args.get("reflection", ""),
        "progress": args.get("progress", ""),
        "remaining_gap": args.get("remaining_gap", ""),
        "mission_complete": args.get("mission_complete", False),
        "mission_reason": args.get("mission_reason", ""),
        "subtasks_status": args.get("subtasks_status", []),
        "notes_to_save": args.get("notes_to_save", []),
    }


# =============================================================================
# 4. Utility Functions
# =============================================================================

def inventory_diff(before, after, max_items=10):
    before_labels = {e["label"] for e in (before or [])}
    after_labels = {e["label"] for e in (after or [])}
    appeared = sorted(after_labels - before_labels)[:max_items]
    disappeared = sorted(before_labels - after_labels)[:max_items]
    return {"appeared": appeared, "disappeared": disappeared}


def format_inventory_diff(diff):
    lines = []
    if diff["appeared"]:
        lines.append(f"  新出现 (×{len(diff['appeared'])}): " + ", ".join(f"'{l}'" for l in diff["appeared"]))
    else:
        lines.append("  新出现: 无")
    if diff["disappeared"]:
        lines.append(f"  消失 (×{len(diff['disappeared'])}): " + ", ".join(f"'{l}'" for l in diff["disappeared"]))
    else:
        lines.append("  消失: 无")
    return "\n".join(lines)


def stitch_images(paths, out_path, axis="horizontal", label=True, gap=10):
    imgs = [Image.open(p).convert("RGB") for p in paths]
    label_h = 40 if label else 0
    if axis == "horizontal":
        h = max(im.height for im in imgs) + label_h
        w = sum(im.width for im in imgs) + gap * (len(imgs) - 1)
        canvas = Image.new("RGB", (w, h), (255, 255, 255))
        x = 0
        for im in imgs:
            canvas.paste(im, (x, label_h))
            x += im.width + gap
    else:
        w = max(im.width for im in imgs)
        h = sum(im.height for im in imgs) + gap * (len(imgs) - 1) + label_h * len(imgs)
        canvas = Image.new("RGB", (w, h), (255, 255, 255))
        y = 0
        for im in imgs:
            y += label_h
            canvas.paste(im, (0, y))
            y += im.height + gap
    if label:
        draw = ImageDraw.Draw(canvas)
        names = ["BEFORE", "AFTER"] if len(imgs) == 2 else [f"IMG{i+1}" for i in range(len(imgs))]
        if axis == "horizontal":
            x = 0
            for i, im in enumerate(imgs):
                draw.text((x + 10, 5), names[i], fill=(0, 0, 0))
                x += im.width + gap
        else:
            y = 0
            for i, im in enumerate(imgs):
                draw.text((10, y + 5), names[i], fill=(0, 0, 0))
                y += label_h + im.height + gap
    canvas.save(out_path)
    return out_path


def render_checklist(plan, plan_state, focus_idx=None):
    if focus_idx is None:
        focus_idx = next((i for i, d in enumerate(plan_state) if not d), -1)
    lines = []
    for i, (task, done) in enumerate(zip(plan, plan_state)):
        marker = "[x]" if done else ("[→]" if i == focus_idx else "[ ]")
        lines.append(f"{marker} {i+1}. {task}")
    return "\n".join(lines)
