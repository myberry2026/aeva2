import subprocess
import time
import xml.etree.ElementTree as ET
import os

def run_adb(cmd):
    return subprocess.run(["adb"] + cmd, capture_output=True, text=True)

def extract_text_from_xml(xml_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        texts = []
        for node in root.iter():
            text = node.get('text')
            if text and text.strip():
                texts.append(text.strip())
        
        seen = set()
        unique_texts = []
        for t in texts:
            if t not in seen:
                unique_texts.append(t)
                seen.add(t)
        return unique_texts
    except Exception as e:
        return [f"Error parsing {xml_path}: {e}"]

def main():
    import os
    work_dir = os.path.dirname(__file__)
    log_file = os.path.join(work_dir, "zhihu_content_steps.txt")
    with open(log_file, "w", encoding="utf-8") as f:
        for i in range(1, 6):
            print(f"Processing Step {i}...")
            f.write(f"{'='*40}\n")
            f.write(f"STEP {i}\n")
            f.write(f"{'='*40}\n")
            
            # Dump UI
            xml_remote = f"/sdcard/step_{i}.xml"
            xml_local = os.path.join(work_dir, f"step_{i}.xml")
            run_adb(["shell", "uiautomator", "dump", xml_remote])
            run_adb(["pull", xml_remote, xml_local])
            
            # Extract Text
            content = extract_text_from_xml(xml_local)
            if content:
                f.write("\n".join(content) + "\n")
            else:
                f.write("[No text found]\n")
            
            f.write("\n\n")
            
            # Screenshot
            img_remote = f"/sdcard/step_{i}.png"
            img_local = os.path.join(work_dir, f"step_{i}.png")
            run_adb(["shell", "screencap", "-p", img_remote])
            run_adb(["pull", img_remote, img_local])
            
            # Scroll
            print(f"Scrolling Step {i}...")
            run_adb(["shell", "input", "swipe", "500", "1800", "500", "400", "500"])
            time.sleep(3)
            
    print(f"Done. Results saved to {log_file}")

if __name__ == "__main__":
    main()
