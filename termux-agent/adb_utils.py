import subprocess
import re
import os
import time

def log(msg):
    print(f"[*] {msg}", flush=True)

def _run_adb(args):
    cmd = ["adb"] + args
    return subprocess.run(cmd, capture_output=True, text=True)

def _adb_get_screen_size():
    out = _run_adb(["shell", "wm", "size"]).stdout or ""
    m = re.search(r'(\d+)x(\d+)', out)
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)

def _adb_get_installed_apps():
    out = _run_adb(["shell", "cmd", "package", "query-activities",
                    "-a", "android.intent.action.MAIN",
                    "-c", "android.intent.category.LAUNCHER"]).stdout or ""
    pkgs = sorted(set(re.findall(r'packageName=([\w.]+)', out)))
    if pkgs: return pkgs
    out2 = _run_adb(["shell", "pm", "list", "packages"]).stdout or ""
    return sorted({line.replace("package:", "").strip() for line in out2.splitlines() if line.strip()})

def _escape_adb_text(text):
    text = text.replace("\\", "\\\\")
    for ch in "&<>'\"()|;`$*?[]{}~#":
        text = text.replace(ch, "\\" + ch)
    return text.replace(" ", "%s")

def _adb_ensure_keyboard():
    pkg = "com.android.adbkeyboard"
    out = _run_adb(["shell", "ime", "list", "-a"]).stdout or ""
    if pkg not in out:
        log("未检测到 ADBKeyBoard，尝试自动下载并安装...")
        # 这里保持简单，如果环境支持直接下
        return False
    
    ime_id = f"{pkg}/.AdbIME"
    if ".AdbIME" not in out: ime_id = f"{pkg}/.ADBKeyboard"
    _run_adb(["shell", "ime", "enable", ime_id])
    _run_adb(["shell", "ime", "set", ime_id])
    return True

EDITOR_CODES = {
    "go":       2,  # IME_ACTION_GO
    "search":   3,  # IME_ACTION_SEARCH
    "send":     4,  # IME_ACTION_SEND
    "next":     5,  # IME_ACTION_NEXT
    "done":     6,  # IME_ACTION_DONE
    "previous": 7,  # IME_ACTION_PREVIOUS
}

def _adb_type(text, clear_first=True, editor_action=None):
    """
    输入文本到当前焦点输入框。
    clear_first: 先清空输入框（默认 True，与旧版行为一致）
    editor_action: 输入后触发 IME 动作（search/send/done/go/next/previous）
    """
    has_adbkb = _adb_ensure_keyboard()
    assert has_adbkb, "请先安装 ADBKeyBoard"

    if clear_first:
        if has_adbkb:
            _run_adb(["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT", "-p", "com.android.adbkeyboard"])
            time.sleep(0.5)
        else:
            _run_adb(["shell", "input", "keyevent", "123"])  # MOVE_END
            time.sleep(0.1)
            _run_adb(["shell", "input", "keyevent"] + ["67"] * 150)
            time.sleep(0.3)

    is_unicode = any(ord(c) > 127 for c in text)
    if has_adbkb:
        # 使用单引号包裹 text，防止被远程 shell 截断（尤其是带空格的文本）
        _run_adb(["shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT", "-p", "com.android.adbkeyboard", "--es", "msg", f"'{text}'"])
        time.sleep(0.5)
    else:
        if is_unicode:
            log("⚠️ 包含中文但未激活 ADBKeyBoard，尝试原生输入（可能乱码）")
        _run_adb(["shell", "input", "text", _escape_adb_text(text)])

    if editor_action and editor_action in EDITOR_CODES and has_adbkb:
        code = EDITOR_CODES[editor_action]
        log(f"📨 触发 IME editor action: {editor_action} (code={code})")
        _run_adb(["shell", "am", "broadcast", "-a", "ADB_EDITOR_CODE", "-p", "com.android.adbkeyboard", "--ei", "code", str(code)])
    elif editor_action and editor_action in EDITOR_CODES:
        log(f"⚠️ editor_action={editor_action} 但 ADBKeyBoard 未激活，退化为 keyevent 66")
        _run_adb(["shell", "input", "keyevent", "66"])
    elif text.endswith("\n"):
        _run_adb(["shell", "input", "keyevent", "66"])
