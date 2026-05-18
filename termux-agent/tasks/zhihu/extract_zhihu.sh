LOG_FILE="zhihu_scrolled_content.txt"
rm -f $LOG_FILE
touch $LOG_FILE

for i in {1..5}
do
    echo "--- Step $i ---" >> $LOG_FILE
    adb shell uiautomator dump /sdcard/dump.xml > /dev/null
    adb pull /sdcard/dump.xml . > /dev/null
    python3 -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('dump.xml')
    root = tree.getroot()
    texts = []
    for node in root.iter():
        text = node.get('text')
        if text and text.strip():
            texts.append(text.strip())
    # 去重并保持顺序
    seen = set()
    unique_texts = [x for x in texts if not (x in seen or seen.add(x))]
    print('\n'.join(unique_texts))
except Exception as e:
    print(f'Error: {e}')
" >> $LOG_FILE
    echo -e "\n" >> $LOG_FILE
    
    # 执行滚动
    adb shell input swipe 500 1800 500 400 300
    sleep 2
done
