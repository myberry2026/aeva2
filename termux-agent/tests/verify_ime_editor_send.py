#!/usr/bin/env python3
import argparse
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "logs" / "ime_editor_send_verify"
ADB_IME = "com.android.adbkeyboard/.AdbIME"


def adb(args, check=True):
    proc = subprocess.run(
        ["adb", *args],
        text=True,
        capture_output=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"adb {' '.join(args)} failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def ensure_adb_keyboard():
    imes = adb(["shell", "ime", "list", "-s"]).stdout
    if "com.android.adbkeyboard" not in imes:
        raise RuntimeError("ADBKeyBoard is not installed.")
    adb(["shell", "ime", "enable", ADB_IME])
    adb(["shell", "ime", "set", ADB_IME])
    time.sleep(0.5)
    current = adb(["shell", "settings", "get", "secure", "default_input_method"]).stdout.strip()
    if "com.android.adbkeyboard" not in current:
        raise RuntimeError(f"ADBKeyBoard is not active: {current}")


def dump_xml(name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    adb(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    xml = adb(["shell", "cat", "/sdcard/ui.xml"]).stdout
    path = OUT_DIR / name
    path.write_text(xml, encoding="utf-8")
    return xml


def screenshot(name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    remote = "/sdcard/ime_editor_send.png"
    adb(["shell", "screencap", "-p", remote])
    adb(["pull", remote, str(OUT_DIR / name)])


def parse_bounds(bounds):
    nums = [int(n) for n in re.findall(r"\d+", bounds or "")]
    if len(nums) != 4:
        return None
    x1, y1, x2, y2 = nums
    return x1, y1, x2, y2


def find_bottom_edit_text(xml):
    root = ET.fromstring(xml)
    candidates = []
    for node in root.iter("node"):
        klass = node.attrib.get("class", "")
        if "EditText" not in klass:
            continue
        bounds = parse_bounds(node.attrib.get("bounds"))
        if not bounds:
            continue
        x1, y1, x2, y2 = bounds
        if x2 <= x1 or y2 <= y1:
            continue
        label = node.attrib.get("text") or node.attrib.get("content-desc") or ""
        candidates.append((y2, x1, y1, x2, label, bounds))
    if not candidates:
        raise RuntimeError("No EditText found in current XML.")
    candidates.sort(reverse=True)
    _, _, _, _, label, bounds = candidates[0]
    x1, y1, x2, y2 = bounds
    return ((x1 + x2) // 2, (y1 + y2) // 2), label, bounds


def screen_size():
    out = adb(["shell", "wm", "size"]).stdout
    match = re.search(r"(\d+)x(\d+)", out)
    if not match:
        raise RuntimeError(f"Cannot parse screen size: {out}")
    return int(match.group(1)), int(match.group(2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", default="10086")
    parser.add_argument("--text", default=f"IME_TEST_{int(time.time())}")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ensure_adb_keyboard()

    adb([
        "shell",
        "am",
        "start",
        "-a",
        "android.intent.action.SENDTO",
        "-d",
        f"smsto:{args.to}",
    ])
    time.sleep(2.0)

    before_xml = dump_xml("before_tap.xml")
    screenshot("before_tap.png")
    try:
        (x, y), label, bounds = find_bottom_edit_text(before_xml)
    except RuntimeError:
        width, height = screen_size()
        x, y = width // 2, height - 110
        label, bounds = "fallback bottom input area", None
    print(f"target_edit_text={label!r} bounds={bounds} tap=({x},{y})")

    adb(["shell", "input", "tap", str(x), str(y)])
    time.sleep(1.0)
    dump_xml("after_ime.xml")
    screenshot("after_ime.png")

    adb(["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"])
    time.sleep(0.2)
    adb(["shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT", "--es", "msg", args.text])
    time.sleep(0.5)
    mid_xml = dump_xml("after_input.xml")
    screenshot("after_input.png")
    print(f"text_visible_before_send={args.text in mid_xml}")

    adb(["shell", "am", "broadcast", "-a", "ADB_EDITOR_CODE", "--ei", "code", "4"])
    time.sleep(3.0)
    after_xml = dump_xml("after_send.xml")
    screenshot("after_send.png")

    input_still_contains = False
    for node in ET.fromstring(after_xml).iter("node"):
        if "EditText" in node.attrib.get("class", "") and args.text in node.attrib.get("text", ""):
            input_still_contains = True
            break

    message_visible_after = args.text in after_xml
    print(f"message_visible_after_send={message_visible_after}")
    print(f"input_still_contains_text={input_still_contains}")
    print(f"artifacts={OUT_DIR}")

    if message_visible_after and not input_still_contains:
        print("PASS: ADB_EDITOR_CODE send submitted the message without clicking a visual send button.")
        return
    raise SystemExit("FAIL: message did not look submitted; inspect artifacts.")


if __name__ == "__main__":
    main()
