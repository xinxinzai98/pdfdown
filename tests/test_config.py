"""测试配置模块"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.utils.config import Config


class TestConfig(unittest.TestCase):
    """配置模块测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        self.assertIsNotNone(config.config)
        self.assertEqual(config.get_output_dir(), "ris_downloads")
        self.assertEqual(config.get_max_workers(), 3)
        self.assertEqual(config.get_max_retries(), 2)

    def test_get_nested_value(self):
        """测试获取嵌套值"""
        config = Config()
        self.assertEqual(config.get("download.max_workers"), 3)
        self.assertEqual(config.get("download.timeout"), 30)
        self.assertIsNone(config.get("nonexistent.key"))

    def test_get_with_default(self):
        """测试默认值"""
        config = Config()
        self.assertEqual(config.get("nonexistent", "default"), "default")

    def test_get_enabled_sources(self):
        """测试获取启用的下载源"""
        config = Config()
        sources = config.get_enabled_sources()
        self.assertIn("Unpaywall", sources)
        self.assertIn("Sci-Hub", sources)

    def test_get_scihub_domains(self):
        """测试获取 Sci-Hub 域名"""
        config = Config()
        domains = config.get_scihub_domains()
        self.assertIsInstance(domains, list)
        self.assertGreater(len(domains), 0)

    def test_get_proxy_config(self):
        """测试获取代理配置"""
        config = Config()
        proxy = config.get_proxy_config(use_china_network=False)
        self.assertIsNotNone(proxy)
        if proxy:
            self.assertIn("http", proxy)

        proxy_china = config.get_proxy_config(use_china_network=True)
        self.assertIsNone(proxy_china)

    def test_load_from_file(self):
        """测试从文件加载配置"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
download:
  max_workers: 5
  output_dir: custom_output
""")
            f.flush()
            config = Config(f.name)
            self.assertEqual(config.get_max_workers(), 5)
            self.assertEqual(config.get_output_dir(), "custom_output")
            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
