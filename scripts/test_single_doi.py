#!/usr/bin/env python3
"""
测试单个 DOI 的 Sci-Hub 下载
"""

import sys
import os

os.environ["NO_PROXY"] = "*"
sys.path.insert(
    0, "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/scripts"
)

from multi_source_ris_downloader_v3 import MultiSourceDownloader

# 使用第一个 DOI
test_doi = "10.1002/adma.202520491"

print("=" * 70)
print("测试单个 DOI 的 Sci-Hub 下载")
print("=" * 70)
print(f"DOI: {test_doi}")
print()

# 创建下载器
downloader = MultiSourceDownloader(max_workers=1, max_retries=0)

# 设置元数据（根据 RIS 文件）
downloader.doi_metadata[test_doi] = {
    "year": "2026",
    "journal": "ADVANCED MATERIALS",
    "first_author": "Miao",
}

print("元数据:")
print(f"  年份: {downloader.doi_metadata[test_doi]['year']}")
print(f"  刊物: {downloader.doi_metadata[test_doi]['journal']}")
print(f"  第一作者: {downloader.doi_metadata[test_doi]['first_author']}")
print()

# 测试文件名生成
filename = downloader.generate_filename(test_doi, "SciHub")
print(f"生成的文件名: {filename}.pdf")
print()

# 直接测试 _try_scihub 方法（不使用代理）
print("开始下载...")
import time

start_time = time.time()

result = downloader._try_scihub(test_doi, proxies=None)

end_time = time.time()
print(f"耗时: {end_time - start_time:.2f} 秒")

print()
print("=" * 70)
if result.get("success"):
    print("✅ Sci-Hub 下载成功!")
    print(f"文件: {result.get('file')}")
    print(f"大小: {result.get('size', 0):,} bytes")
else:
    print("❌ Sci-Hub 下载失败")
print("=" * 70)
