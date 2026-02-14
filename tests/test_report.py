"""测试 HTML 报告生成器"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.utils.report import HTMLReportGenerator


class TestHTMLReportGenerator(unittest.TestCase):
    """HTML 报告生成器测试"""

    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.generator = HTMLReportGenerator(self.test_dir)

    def tearDown(self):
        """清理测试环境"""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_add_item(self):
        """测试添加下载项"""
        self.generator.add_item(
            index=1,
            doi="10.1234/test",
            status="success",
            attempts=[{"source": "Unpaywall", "retry": 1, "status": "success"}],
            final_source="Unpaywall",
            file="/path/to/file.pdf",
            size=1024,
        )

        self.assertEqual(len(self.generator.report_data["items"]), 1)
        item = self.generator.report_data["items"][0]
        self.assertEqual(item["doi"], "10.1234/test")
        self.assertEqual(item["status"], "success")

    def test_update_summary(self):
        """测试更新汇总信息"""
        self.generator.update_summary(total=10, success=8, failed=2)

        self.assertEqual(self.generator.report_data["total"], 10)
        self.assertEqual(self.generator.report_data["success"], 8)
        self.assertEqual(self.generator.report_data["failed"], 2)
        self.assertIsNotNone(self.generator.report_data["end_time"])

    def test_generate_report(self):
        """测试生成 HTML 报告"""
        self.generator.add_item(
            index=1,
            doi="10.1234/test",
            status="success",
            attempts=[{"source": "Unpaywall", "retry": 1, "status": "success"}],
            final_source="Unpaywall",
            file="/path/to/file.pdf",
            size=1024,
        )
        self.generator.update_summary(total=1, success=1, failed=0)

        filepath = self.generator.generate()
        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(filepath.endswith("download_report.html"))

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("10.1234/test", content)
            self.assertIn("Unpaywall", content)

    def test_html_escaping(self):
        """测试 HTML 转义"""
        self.generator.add_item(
            index=1,
            doi='10.1234/<script>alert("xss")</script>',
            status="success",
            attempts=[],
            final_source="Test",
        )
        self.generator.update_summary(total=1, success=1, failed=0)

        filepath = self.generator.generate()
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertNotIn("<script>", content)
            self.assertIn("&lt;script&gt;", content)

    def test_escape_method(self):
        """测试转义方法"""
        result = self.generator._escape('<script>alert("xss")</script>')
        self.assertIn("&lt;", result)
        self.assertIn("&gt;", result)

        result = self.generator._escape(None)
        self.assertEqual(result, "")

        result = self.generator._escape(123)
        self.assertEqual(result, "123")


if __name__ == "__main__":
    unittest.main()
