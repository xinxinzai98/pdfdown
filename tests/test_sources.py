"""测试下载源"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from lib.sources import create_source
from lib.sources.base import BaseSource
from lib.sources.others import ArxivSource, SemanticScholarSource
from lib.sources.unpaywall import UnpaywallSource


class TestSourceRegistry(unittest.TestCase):
    """下载源注册表测试"""

    def test_create_source_unpaywall(self):
        """测试创建 Unpaywall 源"""
        session = requests.Session()
        source = create_source("Unpaywall", session, {})
        self.assertIsInstance(source, UnpaywallSource)

    def test_create_source_arxiv(self):
        """测试创建 arXiv 源"""
        session = requests.Session()
        source = create_source("arXiv", session, {})
        self.assertIsInstance(source, ArxivSource)

    def test_create_unknown_source(self):
        """测试创建未知源"""
        session = requests.Session()
        with self.assertRaises(ValueError):
            create_source("UnknownSource", session, {})


class TestArxivSource(unittest.TestCase):
    """arXiv 下载源测试"""

    def setUp(self):
        self.session = requests.Session()
        self.source = ArxivSource(self.session, {})

    def test_arxiv_doi(self):
        """测试 arXiv DOI 解析"""
        result = self.source.download("10.1234/arxiv.2301.12345")
        self.assertTrue(result.get("success"))
        self.assertIn("pdf_url", result)
        self.assertIn("arxiv.org/pdf", result["pdf_url"])

    def test_non_arxiv_doi(self):
        """测试非 arXiv DOI"""
        result = self.source.download("10.1234/normal.paper")
        self.assertFalse(result.get("success"))


class TestUnpaywallSource(unittest.TestCase):
    """Unpaywall 下载源测试"""

    def setUp(self):
        self.session = requests.Session()
        self.source = UnpaywallSource(self.session, {"email": "test@test.com"})

    @patch("requests.Session.get")
    def test_unpaywall_open_access(self, mock_get):
        """测试开放获取文献"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "is_oa": True,
            "best_oa_location": {"url": "https://example.com/paper.pdf"},
        }
        mock_get.return_value = mock_response

        result = self.source.download("10.1234/open.paper")

        self.assertTrue(result.get("success"))
        self.assertEqual(result["pdf_url"], "https://example.com/paper.pdf")

    @patch("requests.Session.get")
    def test_unpaywall_not_open_access(self, mock_get):
        """测试非开放获取文献"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"is_oa": False}
        mock_get.return_value = mock_response

        result = self.source.download("10.1234/closed.paper")

        self.assertFalse(result.get("success"))


class TestSemanticScholarSource(unittest.TestCase):
    """Semantic Scholar 下载源测试"""

    def setUp(self):
        self.session = requests.Session()
        self.source = SemanticScholarSource(self.session, {})

    @patch("requests.Session.get")
    def test_semantic_scholar_open_access(self, mock_get):
        """测试开放获取"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "openAccessPdf": {"url": "https://example.com/paper.pdf"}
        }
        mock_get.return_value = mock_response

        result = self.source.download("10.1234/test.paper")

        self.assertTrue(result.get("success"))


if __name__ == "__main__":
    unittest.main()
