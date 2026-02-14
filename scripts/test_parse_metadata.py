#!/usr/bin/env python3
"""
测试 RIS 元数据解析
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
print("测试 RIS 元数据解析")
print("=" * 70)
print(f"RIS 文件: {ris_file}")
print()

# 创建下载器
downloader = MultiSourceDownloader()

import time

start_time = time.time()

# 解析元数据
print("开始解析...")
metadata = downloader.parse_ris_metadata(ris_file)

end_time = time.time()
print(f"✅ 解析完成，耗时: {end_time - start_time:.2f} 秒")
print(f"   共 {len(metadata)} 条元数据")
print()

# 显示前 3 条
for i, (doi, meta) in enumerate(list(metadata.items())[:3], 1):
    print(f"[{i}] DOI: {doi}")
    print(f"    年份: {meta.get('year', 'N/A')}")
    print(f"    刊物: {meta.get('journal', 'N/A')}")
    print(f"    第一作者: {meta.get('first_author', 'N/A')}")

print("=" * 70)
