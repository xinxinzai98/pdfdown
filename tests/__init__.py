"""测试包"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .test_config import TestConfig
from .test_validator import TestValidator
from .test_report import TestHTMLReportGenerator
from .test_sources import (
    TestArxivSource,
    TestSemanticScholarSource,
    TestSourceRegistry,
    TestUnpaywallSource,
)
from .test_downloader import TestMultiSourceDownloader


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestHTMLReportGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestSourceRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestArxivSource))
    suite.addTests(loader.loadTestsFromTestCase(TestUnpaywallSource))
    suite.addTests(loader.loadTestsFromTestCase(TestSemanticScholarSource))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiSourceDownloader))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
