#!/usr/bin/env python3
"""
测试使用正确元数据的 Sci-Hub 下载
"""

import sys
import os

os.environ["NO_PROXY"] = "*"
sys.path.insert(
    0, "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/scripts"
)

from multi_source_ris_downloader_v3 import MultiSourceDownloader

# 使用 RIS 文件中的 DOI
test_doi = "10.3390/pr8020248"

print("=" * 70)
print("测试使用正确元数据的 Sci-Hub 下载")
print("=" * 70)
print(f"DOI: {test_doi}")
print()

# 创建下载器
downloader = MultiSourceDownloader(max_workers=1, max_retries=0)

# 解析元数据
metadata = downloader.parse_ris_metadata(
    "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/savedrecs.ris"
)
downloader.doi_metadata = metadata

# 显示元数据
if test_doi in downloader.doi_metadata:
    meta = downloader.doi_metadata[test_doi]
    print("元数据:")
    print(f"  年份: {meta.get('year', 'N/A')}")
    print(f"  刊物: {meta.get('journal', 'N/A')}")
    print(f"  第一作者: {meta.get('first_author', 'N/A')}")
    print()

    # 测试文件名生成
    filename = downloader.generate_filename(test_doi, "SciHub")
    print(f"生成的文件名: {filename}.pdf")
    print()

    # 下载
    print("开始下载...")
    result = downloader._try_scihub(test_doi, proxies=None)

    print()
    print("=" * 70)
    if result.get("success"):
        print("✅ 下载成功!")
        print(f"文件: {result.get('file')}")
        print(f"大小: {result.get('size', 0):,} bytes")
    else:
        print("❌ 下载失败")
    print("=" * 70)
else:
    print("❌ 未找到 DOI 的元数据")
