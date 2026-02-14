#!/usr/bin/env python3
"""
快速测试 - 测试修复后的批量下载
"""

import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(__file__))

from multi_source_ris_downloader_v3 import MultiSourceDownloader


def test_batch_download(ris_file, n=3):
    """测试批量下载"""

    print("=" * 70)
    print(f"🧪 批量下载测试 (前 {n} 个 DOI) - Unpaywall 已修复")
    print("=" * 70)

    # 提取 DOI
    dois = []
    with open(ris_file, "r", encoding="utf-8") as f:
        content = f.read()

    doi_pattern = re.compile(r"^DO\s*-\s*(.+)$", re.MULTILINE)
    matches = doi_pattern.findall(content)

    for doi in matches:
        doi = doi.strip()
        if doi and doi not in dois:
            dois.append(doi)

    selected_dois = dois[:n]

    print(f"\n📄 RIS 文件: {ris_file}")
    print(f"📋 总共找到 {len(dois)} 个 DOI, 测试前 {len(selected_dois)} 个:")
    for i, doi in enumerate(selected_dois, 1):
        print(f"  [{i}] {doi}")

    print(f"\n🚀 开始测试...")
    print("=" * 70)

    downloader = MultiSourceDownloader(max_workers=1, max_retries=1)
    downloader.html_report["total"] = len(selected_dois)

    start_time = time.time()

    for i, doi in enumerate(selected_dois, 1):
        print(f"\n[{i}/{len(selected_dois)}] {doi}")
        print("-" * 70)

        try:
            success = downloader.download_doi(doi, index=i, total=len(selected_dois))

            if success:
                print(f"✅ {doi} 下载成功")
            else:
                print(f"❌ {doi} 所有来源均失败")

        except Exception as e:
            print(f"❌ {doi} 发生异常: {e}")

        time.sleep(1)

    elapsed_time = time.time() - start_time
    downloader.html_report["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    downloader.html_report["success"] = len(downloader.results["success"])
    downloader.html_report["failed"] = len(downloader.results["failed"])

    print("\n" + "=" * 70)
    print(f"✅ 测试完成! 总耗时: {elapsed_time:.1f} 秒")
    print("=" * 70)

    downloader.print_summary(selected_dois)


if __name__ == "__main__":
    ris_file = "../savedrecs.ris"
    n = 3

    if len(sys.argv) > 1:
        ris_file = sys.argv[1]
    if len(sys.argv) > 2:
        n = int(sys.argv[2])

    test_batch_download(ris_file, n)
