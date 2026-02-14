"""测试下载器"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.core.downloader import MultiSourceDownloader
from lib.utils.config import Config


class TestMultiSourceDownloader(unittest.TestCase):
    """多来源下载器测试"""

    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.config = Config()
        self.config._config["download"]["output_dir"] = self.test_dir
        self.config._config["download"]["validate_pdf"] = False
        self.config._config["logging"]["console"] = False

    def tearDown(self):
        """清理测试环境"""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init(self):
        """测试初始化"""
        downloader = MultiSourceDownloader(config=self.config)

        self.assertIsNotNone(downloader.session)
        self.assertEqual(downloader.output_dir, self.test_dir)
        self.assertGreater(len(downloader.sources), 0)

    def test_init_with_custom_params(self):
        """测试使用自定义参数初始化"""
        downloader = MultiSourceDownloader(
            config=self.config, max_workers=5, max_retries=3
        )

        self.assertEqual(downloader.max_workers, 5)
        self.assertEqual(downloader.max_retries, 3)

    def test_generate_filename(self):
        """测试生成文件名"""
        downloader = MultiSourceDownloader(config=self.config)
        downloader.doi_metadata = {
            "10.1234/test": {
                "year": "2024",
                "journal": "Test Journal",
                "first_author": "Smith",
            }
        }

        filename = downloader.generate_filename("10.1234/test", "Unpaywall")

        self.assertIn("2024", filename)
        self.assertIn("Test Journal", filename)
        self.assertIn("Smith", filename)
        self.assertIn("Unpaywall", filename)

    def test_parse_ris_metadata(self):
        """测试解析 RIS 元数据"""
        ris_content = """TY  - JOUR
AU  - Smith, John
TI  - Test Paper
T2  - Test Journal
PY  - 2024
DO  - 10.1234/test
ER  -

TY  - JOUR
AU  - Doe, Jane
TI  - Another Paper
T2  - Another Journal
PY  - 2023
DO  - 10.5678/another
ER  -
"""
        ris_file = os.path.join(self.test_dir, "test.ris")
        with open(ris_file, "w", encoding="utf-8") as f:
            f.write(ris_content)

        downloader = MultiSourceDownloader(config=self.config)
        metadata = downloader.parse_ris_metadata(ris_file)

        self.assertEqual(len(metadata), 2)
        self.assertIn("10.1234/test", metadata)
        self.assertIn("10.5678/another", metadata)

        self.assertEqual(metadata["10.1234/test"]["year"], "2024")
        self.assertEqual(metadata["10.1234/test"]["first_author"], "Smith")
        self.assertEqual(metadata["10.5678/another"]["year"], "2023")

    @patch("lib.core.downloader.create_source")
    def test_download_doi_success(self, mock_create_source):
        """测试下载成功"""
        mock_source = MagicMock()
        mock_source.download.return_value = {
            "success": True,
            "pdf_url": "https://example.com/paper.pdf",
        }
        mock_create_source.return_value = mock_source

        downloader = MultiSourceDownloader(config=self.config)

        with patch.object(downloader, "_download_and_save") as mock_save:
            mock_save.return_value = {
                "success": True,
                "file": os.path.join(self.test_dir, "test.pdf"),
                "size": 1024,
            }

            result = downloader.download_doi("10.1234/test", index=1, total=1)
            self.assertTrue(result)

    @patch("lib.core.downloader.create_source")
    def test_download_doi_all_sources_fail(self, mock_create_source):
        """测试所有来源均失败"""
        mock_source = MagicMock()
        mock_source.download.return_value = {"success": False, "error": "Not found"}
        mock_create_source.return_value = mock_source

        downloader = MultiSourceDownloader(config=self.config)
        downloader.max_retries = 0

        result = downloader.download_doi("10.1234/nonexistent", index=1, total=1)
        self.assertFalse(result)
        self.assertIn("10.1234/nonexistent", downloader.results["failed"])


if __name__ == "__main__":
    unittest.main()
