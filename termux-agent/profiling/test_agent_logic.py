
import unittest
import os
import xml.etree.ElementTree as ET
from profiling.smart_coffee_agent import SmartAgent

class TestSmartAgent(unittest.TestCase):
    def setUp(self):
        self.agent = SmartAgent()
        # 创建一个模拟的 XML 文件
        self.test_xml = "profiling/test_bounds.xml"
        content = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
        <hierarchy rotation="0">
            <node index="0" text="Call" bounds="[100,100][200,200]" />
            <node index="1" text="408-123-4567" bounds="[300,300][400,400]" />
        </hierarchy>
        """
        with open(self.test_xml, "w") as f:
            f.write(content)

    def test_get_bounds(self):
        # 测试寻找 "Call" 按钮
        pos = self.agent.get_bounds(self.test_xml, "Call")
        self.assertEqual(pos, (150, 150))
        
        # 测试正则匹配号码
        pos_phone = self.agent.get_bounds(self.test_xml, r"\d{3}-\d{3}-\d{4}")
        self.assertEqual(pos_phone, (350, 350))

    def tearDown(self):
        if os.path.exists(self.test_xml):
            os.remove(self.test_xml)

if __name__ == "__main__":
    unittest.main()
