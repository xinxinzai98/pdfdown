#!/usr/bin/env python3
"""
简单测试 Sci-Hub 下载
"""

import sys
import os

os.environ["NO_PROXY"] = "*"
sys.path.insert(
    0, "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/scripts"
)

from multi_source_ris_downloader_v3 import MultiSourceDownloader

# 使用已知可用的 DOI
test_doi = "10.3390/pr8020248"

print("=" * 70)
print("简单测试 Sci-Hub 下载")
print("=" * 70)
print(f"DOI: {test_doi}")
print()

# 创建下载器
downloader = MultiSourceDownloader(max_workers=1, max_retries=0)

# 设置元数据
downloader.doi_metadata[test_doi] = {
    "year": "2020",
    "journal": "Processes",
    "first_author": "Miao",
}

# 直接测试 _try_scihub 方法
print("测试 Sci-Hub 下载方法...")
proxies = downloader.get_proxy_config(use_china_network=False)
result = downloader._try_scihub(test_doi, proxies=proxies)

print()
print("=" * 70)
if result.get("success"):
    print("✅ Sci-Hub 下载成功!")
    print(f"文件: {result.get('file')}")
    print(f"大小: {result.get('size', 0):,} bytes")
else:
    print("❌ Sci-Hub 下载失败")
print("=" * 70)
