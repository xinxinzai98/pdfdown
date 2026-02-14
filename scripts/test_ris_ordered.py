#!/usr/bin/env python3
"""
测试 RIS 文件批量下载（按顺序，不使用代理）
"""

import sys
import os
import re

os.environ["NO_PROXY"] = "*"
sys.path.insert(
    0, "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/scripts"
)

from multi_source_ris_downloader_v3 import MultiSourceDownloader

ris_file = "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/savedrecs.ris"

print("=" * 70)
print("测试 RIS 文件批量下载（按顺序，不使用代理）")
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

# 按照 RIS 文件顺序获取前 3 个 DOI
test_dois = []
with open(ris_file, "r", encoding="utf-8") as f:
    content = f.read()
    doi_pattern = re.compile(r"^DO\s*-\s*(.+)$", re.MULTILINE)
    matches = doi_pattern.findall(content)
    for doi in matches:
        doi = doi.strip()
        if doi and doi not in test_dois:
            test_dois.append(doi)
        if len(test_dois) >= 3:
            break

print(f"📋 测试前 {len(test_dois)} 个 DOI:")
for i, doi in enumerate(test_dois, 1):
    metadata = downloader.doi_metadata.get(doi, {})
    print(f"  [{i}] {doi}")
    print(
        f"      {metadata.get('year', 'N/A')} - {metadata.get('journal', 'N/A')} - {metadata.get('first_author', 'N/A')}"
    )

print(f"\n🚀 开始下载（不使用代理）...")
print("=" * 70)

success_count = 0
for i, doi in enumerate(test_dois, 1):
    print(f"\n[{i}/{len(test_dois)}] 处理 DOI: {doi}")

    # 只测试 Sci-Hub 下载（不使用代理）
    result = downloader._try_scihub(doi, proxies=None)

    if result.get("success"):
        success_count += 1
        print(f"  ✅ 下载成功")
        print(f"     文件: {result.get('file')}")
        print(f"     大小: {result.get('size', 0):,} bytes")
    else:
        print(f"  ❌ 下载失败")

print("\n" + "=" * 70)
print(f"📊 下载总结")
print("=" * 70)
print(f"成功: {success_count}/{len(test_dois)}")
success_rate = (success_count / len(test_dois)) * 100 if test_dois else 0
print(f"成功率: {success_rate:.1f}%")
print("=" * 70)
