#!/usr/bin/env python3
"""
测试前 2 个 DOI 的批量下载
"""

import sys
import os

os.environ["NO_PROXY"] = "*"
sys.path.insert(
    0, "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/scripts"
)

from multi_source_ris_downloader_v3 import MultiSourceDownloader

# 测试 DOIs
test_dois = [
    "10.1002/adma.202520491",
    "10.1016/j.apenergy.2025.126643",
]

print("=" * 70)
print("测试前 2 个 DOI 下载")
print("=" * 70)
print(f"DOI 数量: {len(test_dois)}")
for i, doi in enumerate(test_dois, 1):
    print(f"  [{i}] {doi}")
print()

# 创建下载器
downloader = MultiSourceDownloader(max_workers=1, max_retries=1)

# 逐个下载
success_count = 0
for i, doi in enumerate(test_dois, 1):
    print(f"\n[{i}/{len(test_dois)}] 处理 DOI: {doi}")
    result = downloader.download_doi(doi, i, len(test_dois))
    if result:
        success_count += 1
        print(f"  ✅ 下载成功")
    else:
        print(f"  ❌ 下载失败")

print("\n" + "=" * 70)
print(f"总结: {success_count}/{len(test_dois)} 下载成功")
print("=" * 70)

# 生成报告
downloader.print_summary(test_dois)
downloader.generate_html_report()
