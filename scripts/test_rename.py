#!/usr/bin/env python3
"""
测试文件重命名功能
"""

import sys
import os

os.environ["NO_PROXY"] = "*"
sys.path.insert(
    0, "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/scripts"
)

from multi_source_ris_downloader_v3 import MultiSourceDownloader

ris_file = "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/savedrecs.ris"

print("=" * 70)
print("测试 RIS 元数据解析和文件重命名")
print("=" * 70)
print(f"RIS 文件: {ris_file}")
print()

# 创建下载器
downloader = MultiSourceDownloader(max_workers=1, max_retries=0)

# 解析元数据并保存到 downloader.doi_metadata
downloader.doi_metadata = downloader.parse_ris_metadata(ris_file)

print(f"✅ 解析到 {len(downloader.doi_metadata)} 条元数据")
print()

# 显示前 3 条元数据
for i, (doi, meta) in enumerate(list(downloader.doi_metadata.items())[:3], 1):
    print(f"[{i}] DOI: {doi}")
    print(f"    年份: {meta.get('year', 'N/A')}")
    print(f"    刊物: {meta.get('journal', 'N/A')}")
    print(f"    第一作者: {meta.get('first_author', 'N/A')}")

    # 测试文件名生成
    filename = downloader.generate_filename(doi, "SciHub")
    print(f"    文件名: {filename}.pdf")
    print()

print("=" * 70)
print("测试 RIS 元数据解析和文件重命名")
print("=" * 70)
print(f"RIS 文件: {ris_file}")
print()

# 创建下载器
downloader = MultiSourceDownloader(max_workers=1, max_retries=0)

# 解析元数据
metadata = downloader.parse_ris_metadata(ris_file)

print(f"✅ 解析到 {len(metadata)} 条元数据")
print()

# 显示前 3 条元数据
for i, (doi, meta) in enumerate(list(metadata.items())[:3], 1):
    print(f"[{i}] DOI: {doi}")
    print(f"    年份: {meta.get('year', 'N/A')}")
    print(f"    刊物: {meta.get('journal', 'N/A')}")
    print(f"    第一作者: {meta.get('first_author', 'N/A')}")

    # 测试文件名生成
    filename = downloader.generate_filename(doi, "SciHub")
    print(f"    文件名: {filename}.pdf")
    print()

print("=" * 70)
