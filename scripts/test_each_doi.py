#!/usr/bin/env python3
"""
逐个测试 DOI 下载（带超时）
"""

import sys
import os

os.environ["NO_PROXY"] = "*"
sys.path.insert(
    0, "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/scripts"
)

from multi_source_ris_downloader_v3 import MultiSourceDownloader

ris_file = "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/savedrecs.ris"

# 创建下载器
downloader = MultiSourceDownloader(max_workers=1, max_retries=0)

# 解析元数据
metadata = downloader.parse_ris_metadata(ris_file)

print("=" * 70)
print("逐个测试 DOI 下载（仅 Sci-Hub，不使用代理）")
print("=" * 70)
print(f"共 {len(metadata)} 个 DOI")
print()

success_count = 0
for i, (doi, meta) in enumerate(metadata.items(), 1):
    print(f"[{i}/{len(metadata)}] DOI: {doi}")
    print(
        f"    {meta.get('year', 'N/A')} - {meta.get('journal', 'N/A')} - {meta.get('first_author', 'N/A')}"
    )

    # 下载
    result = downloader._try_scihub(doi, proxies=None)

    if result.get("success"):
        success_count += 1
        print(f"    ✅ 成功 - {result.get('file')} ({result.get('size', 0):,} bytes)")
    else:
        print(f"    ❌ 失败")
    print()

print("=" * 70)
print(
    f"成功率: {success_count}/{len(metadata)} = {(success_count / len(metadata) * 100):.1f}%"
)
print("=" * 70)
