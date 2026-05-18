"""
screen_converter.py — 统一 UI 转换器 (XML / JSON -> Agent Inventory)
支持 ADB (XML) 和 Bridge (JSON) 两种后端。
"""

import re
import xml.etree.ElementTree as ET

def build_label(text, desc, res_id, cls, is_edit):
    """统一的标签构建逻辑。"""
    label_parts = []
    text = (text or "").strip()
    desc = (desc or "").strip()
    res_id = res_id or ""
    simple_id = res_id.split("/")[-1] if "/" in res_id else res_id
    cls_name = cls.split(".")[-1] if cls else ""

    if text and len(text) < 50:
        label_parts.append(f"'{text}'")
    if desc and len(desc) < 50:
        label_parts.append(f"desc:'{desc}'")
    if simple_id:
        label_parts.append(f"id:{simple_id}")
    if is_edit:
        label_parts.append(f"({cls_name})")

    return " ".join(label_parts) or cls_name or "Widget"

def is_node_interactive(clickable, focusable, long_clickable, is_edit, simple_id):
    """统一的交互判定逻辑。"""
    return (
        clickable or focusable or long_clickable or is_edit or
        "search" in (simple_id or "").lower()
    )

def _assign_ids(elements):
    """为展平后的节点分配 ID。"""
    for i, e in enumerate(elements):
        e["id"] = i
    return elements

# === 1. ADB XML 解析分支 ===

def xml_to_inventory(xml_str, screen_w=1080):
    """将 ADB uiautomator dump 的 XML 转换为清单。"""
    if not xml_str: return []
    try:
        root = ET.fromstring(xml_str)
    except Exception:
        return []
    
    elements = []
    bounds_re = re.compile(r'\d+')
    max_w = int(screen_w * 0.99)

    for node in root.iter():
        if node.tag != 'node': continue
        a = node.attrib
        bounds_str = a.get('bounds', '')
        if not bounds_str: continue

        # 提取基础属性
        cls = a.get('class', '')
        is_edit = "Edit" in cls or "EditText" in cls
        res_id = a.get('resource-id') or ""
        simple_id = res_id.split("/")[-1] if "/" in res_id else res_id
        
        clickable = a.get('clickable') == 'true'
        focusable = a.get('focusable') == 'true'
        long_clickable = a.get('long-clickable') == 'true'
        
        # 判定
        interactive = is_node_interactive(clickable, focusable, long_clickable, is_edit, simple_id)
        text = a.get('text', '')
        desc = a.get('content-desc', '')

        if (text or desc or interactive):
            b = bounds_re.findall(bounds_str)
            if len(b) == 4:
                x1, y1, x2, y2 = map(int, b)
                w, h = x2 - x1, y2 - y1
                if w < 5 or h < 5 or w > max_w: continue
                
                label = build_label(text, desc, res_id, cls, is_edit)
                elements.append({
                    "label": label,
                    "pos": [(x1 + x2) // 2, (y1 + y2) // 2],
                    "bounds": {"left": x1, "top": y1, "right": x2, "bottom": y2}
                })
    
    return _assign_ids(elements)

# === 2. Bridge JSON 解析分支 ===

def json_to_inventory(json_obj, screen_w=1080):
    """将 Bridge ScreenNode JSON 转换为清单。"""
    if not json_obj: return []
    
    # 自动解包常用的包装格式
    root = json_obj
    if isinstance(json_obj, dict):
        if "tree" in json_obj: root = json_obj["tree"]
        elif "data" in json_obj: root = json_obj["data"]

    results = []
    def _recurse(node):
        if not isinstance(node, dict): return
        
        # 提取属性
        cls = node.get("className", "")
        is_edit = "Edit" in cls or "EditText" in cls
        res_id = node.get("resourceId") or ""
        simple_id = res_id.split("/")[-1] if "/" in res_id else res_id
        
        clickable = node.get("clickable", False)
        focusable = node.get("focusable", False)
        long_clickable = node.get("longClickable", False) or node.get("long-clickable", False)
        
        interactive = is_node_interactive(clickable, focusable, long_clickable, is_edit, simple_id)
        text = node.get("text", "")
        desc = node.get("contentDescription", "")
        bounds = node.get("bounds")

        if (text or desc or interactive) and bounds:
            l, t, r, b = bounds.get("left", 0), bounds.get("top", 0), bounds.get("right", 0), bounds.get("bottom", 0)
            w, h = r - l, b - t
            if w >= 5 and h >= 5 and w <= int(screen_w * 0.99):
                label = build_label(text, desc, res_id, cls, is_edit)
                results.append({
                    "label": label,
                    "pos": [(l + r) // 2, (t + b) // 2],
                    "bounds": {"left": l, "top": t, "right": r, "bottom": b}
                })
        
        for child in node.get("children", []):
            _recurse(child)

    if isinstance(root, list):
        for n in root: _recurse(n)
    else:
        _recurse(root)
        
    return _assign_ids(results)

# 保持兼容性用的别名
def screen_to_inventory(data, screen_w=1080):
    if isinstance(data, str) and (data.strip().startswith("<") or "<?xml" in data):
        return xml_to_inventory(data, screen_w)
    return json_to_inventory(data, screen_w)

def format_inventory_diff(old_inv, new_inv):
    """简单对比两组清单，返回人类可读的差异字符串。"""
    old_labels = {item['label'] for item in old_inv}
    new_labels = {item['label'] for item in new_inv}
    
    added = new_labels - old_labels
    removed = old_labels - new_labels
    
    parts = []
    if added:
        parts.append(f"新增控件: {', '.join(list(added)[:5])}" + ("..." if len(added) > 5 else ""))
    if removed:
        parts.append(f"消失控件: {', '.join(list(removed)[:5])}" + ("..." if len(removed) > 5 else ""))
        
    return " | ".join(parts) if parts else "UI 无显著变化"
