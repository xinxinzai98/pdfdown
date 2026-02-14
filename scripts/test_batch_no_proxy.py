#!/usr/bin/env python3
"""
测试不使用代理的批量下载
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
print("测试不使用代理的批量下载")
print("=" * 70)
print(f"RIS 文件: {ris_file}")
print()

# 创建下载器
downloader = MultiSourceDownloader(max_workers=1, max_retries=0)

# 解析元数据
print("📖 解析 RIS 元数据...")
downloader.doi_metadata = downloader.parse_ris_metadata(ris_file)
print(f"   ✅ 解析完成，共 {len(downloader.doi_metadata)} 条元数据")
print()

# 只下载前 2 个 DOI
test_dois = list(downloader.doi_metadata.keys())[:2]
print(f"📋 测试前 {len(test_dois)} 个 DOI:")

success_count = 0
for i, doi in enumerate(test_dois, 1):
    metadata = downloader.doi_metadata.get(doi, {})
    print(f"  [{i}] {doi}")
    print(
        f"      {metadata.get('year', 'N/A')} - {metadata.get('journal', 'N/A')} - {metadata.get('first_author', 'N/A')}"
    )

print()
print(f"\n🚀 开始下载（不使用代理）...")
print("=" * 70)

# 直接调用 _try_scihub 方法（不使用代理）
for i, doi in enumerate(test_dois, 1):
    print(f"\n[{i}/{len(test_dois)}] 处理 DOI: {doi}")

    # 测试 Sci-Hub 下载
    result = downloader._try_scihub(doi, proxies=None)

    if result.get("success"):
        success_count += 1
        print(f"  ✅ 下载成功")
        print(f"     文件: {result.get('file')}")
        print(f"     大小: {result.get('size', 0):,} bytes")
    else:
        print(f"  ❌ 下载失败")

print("\n" + "=" * 70)
print(f"总结: {success_count}/{len(test_dois)} 下载成功")
print("=" * 70)
