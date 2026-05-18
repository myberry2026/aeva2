import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from screen_converter import xml_to_inventory

def test_inventory(xml_path):
    SCREEN_W = 1080
    with open(xml_path, 'r') as f:
        xml_data = f.read()
    
    elements = xml_to_inventory(xml_data, SCREEN_W)
    
    print(f"Total elements found: {len(elements)}")
    for e in elements:
        print(f"ID {e['id']}: {e['label']} @ {e['pos']}")

if __name__ == "__main__":
    test_inventory("logs/latest_ui.xml")
