#!/usr/bin/env python3
"""
测试完整的下载流程（带文件重命名）
"""

import sys
import os

os.environ["NO_PROXY"] = "*"
sys.path.insert(
    0, "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/scripts"
)

from multi_source_ris_downloader_v3 import MultiSourceDownloader

# 测试 DOI（已知可用的）
test_doi = "10.3390/pr8020248"

print("=" * 70)
print("测试完整下载流程（带文件重命名）")
print("=" * 70)
print(f"DOI: {test_doi}")
print()

# 创建下载器
downloader = MultiSourceDownloader(max_workers=1, max_retries=1)

# 手动设置元数据（模拟从 RIS 文件解析）
downloader.doi_metadata[test_doi] = {
    "year": "2020",
    "journal": "Processes",
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

# 测试下载
print("开始下载...")
result = downloader.download_doi(test_doi, 1, 1)

print()
print("=" * 70)
if result:
    print("✅ 下载成功!")
else:
    print("❌ 下载失败")
print("=" * 70)
