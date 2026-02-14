#!/usr/bin/env python3
"""
直接测试 Unpaywall 下载方法
"""

import sys
import os

os.environ["NO_PROXY"] = "*"
sys.path.insert(
    0, "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/scripts"
)

from multi_source_ris_downloader_v3 import MultiSourceDownloader

# 使用已知可以下载的 DOI（open access）
test_doi = "10.3390/pr8020248"

print("=" * 70)
print("测试 Unpaywall 下载方法")
print("=" * 70)
print(f"DOI: {test_doi}")
print()

# 创建下载器
downloader = MultiSourceDownloader(max_workers=1, max_retries=1)

# 测试 Unpaywall 方法
print("测试 Unpaywall API 下载...")
result = downloader._try_unpaywall(test_doi, proxies=None)

print()
print("=" * 70)
if result.get("success"):
    print("✅ Unpaywall 测试成功!")
    print(f"文件: {result.get('file')}")
    print(f"大小: {result.get('size', 0):,} bytes")
else:
    print("❌ Unpaywall 测试失败")
    if "error" in result:
        print(f"错误: {result['error']}")
print("=" * 70)
