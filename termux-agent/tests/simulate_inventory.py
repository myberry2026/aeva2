import sys
import xml.etree.ElementTree as ET
import re

def get_ui_inventory_mock(xml_path, SCREEN_W=1080, SCREEN_H=2400):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return []

    elements = []
    idx = 0
    max_w = int(SCREEN_W * 0.99)
    bounds_re = re.compile(r'-?\d+')
    
    for node in root.iter('node'):
        a = node.attrib
        text = a.get('text', '').strip()
        desc = a.get('content-desc', '').strip()
        res_id = a.get('resource-id', '').split('/')[-1]
        cls = a.get('class', '').split('.')[-1]
        
        is_edit = "Edit" in cls or "EditText" in cls
        is_interactive = (
            a.get('clickable') == 'true' or 
            a.get('focusable') == 'true' or 
            a.get('long-clickable') == 'true' or
            is_edit or
            "search" in res_id.lower()
        )

        if (text or desc or is_interactive) and a.get('bounds'):
            b = bounds_re.findall(a.get('bounds'))
            if len(b) == 4:
                x1, y1, x2, y2 = map(int, b)
                if (x2-x1) < 5 or (y2-y1) < 5 or (x2-x1) > max_w: continue
                
                label_parts = []
                if text and len(text) < 50: label_parts.append(f"'{text}'")
                if desc and len(desc) < 50: label_parts.append(f"desc:'{desc}'")
                if res_id: label_parts.append(f"id:{res_id}")
                if is_edit: label_parts.append(f"({cls})")
                
                label = " ".join(label_parts) or cls or "Widget"
                elements.append({"id": idx, "label": label, "pos": [(x1+x2)//2, (y1+y2)//2]})
                idx += 1
    return elements

if __name__ == "__main__":
    elements = get_ui_inventory_mock(sys.argv[1])
    list_str = "\n".join([f"ID {e['id']}: {e['label']} @ {e['pos']}" for e in elements])
    print(list_str)
