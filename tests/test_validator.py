"""测试 PDF 验证模块"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.utils.validator import clean_invalid_pdfs, scan_directory, validate_pdf


class TestValidator(unittest.TestCase):
    """PDF 验证模块测试"""

    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理测试环境"""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_pdf(self, filename: str, content: bytes) -> str:
        """创建测试 PDF 文件"""
        filepath = os.path.join(self.test_dir, filename)
        with open(filepath, "wb") as f:
            f.write(content)
        return filepath

    def test_validate_valid_pdf(self):
        """测试验证有效的 PDF"""
        pdf_content = b"%PDF-1.4\n" + b"x" * 200 + b"\n%EOF"
        filepath = self._create_pdf("valid.pdf", pdf_content)

        valid, msg = validate_pdf(filepath)
        self.assertTrue(valid, f"Expected valid PDF, got: {msg}")

    def test_validate_incomplete_pdf(self):
        """测试验证不完整的 PDF"""
        pdf_content = b"%PDF-1.4\ncontent without EOF marker" * 10
        filepath = self._create_pdf("incomplete.pdf", pdf_content)
        valid, msg = validate_pdf(filepath)
        self.assertFalse(valid)
        self.assertIn("文件尾无效", msg)

    def test_scan_directory(self):
        """测试扫描目录"""
        self._create_pdf("valid.pdf", b"%PDF-1.4\n" + b"x" * 200 + b"\n%EOF")
        self._create_pdf("invalid.pdf", b"Not a PDF" * 100)
        self._create_pdf("small.pdf", b"tiny")

        stats = scan_directory(self.test_dir)

        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["valid"], 1)
        self.assertEqual(stats["invalid"], 2)

    def test_clean_invalid_pdfs(self):
        """测试清理无效 PDF"""
        self._create_pdf("valid.pdf", b"%PDF-1.4\n" + b"x" * 200 + b"\n%EOF")
        self._create_pdf("invalid.pdf", b"Not a PDF" * 100)

        deleted = clean_invalid_pdfs(self.test_dir)

        self.assertEqual(len(deleted), 1)
        self.assertIn("invalid.pdf", deleted)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "valid.pdf")))

    def test_scan_empty_directory(self):
        """测试扫描空目录"""
        stats = scan_directory(self.test_dir)
        self.assertEqual(stats["total"], 0)

    def test_scan_nonexistent_directory(self):
        """测试扫描不存在的目录"""
        stats = scan_directory("/nonexistent/directory")
        self.assertEqual(stats["total"], 0)


if __name__ == "__main__":
    unittest.main()
