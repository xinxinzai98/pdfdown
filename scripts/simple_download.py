#!/usr/bin/env python3
"""
简化的批量下载器 - 直接测试
"""

import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(__file__))

from multi_source_ris_downloader_v3 import MultiSourceDownloader


def simple_batch_download(ris_file):
    """简化的批量下载"""

    print("=" * 70)
    print("📚 简化批量下载器 - savedrecs.ris")
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

    print(f"\n📄 RIS 文件: {ris_file}")
    print(f"📋 找到 {len(dois)} 个 DOI:")
    for i, doi in enumerate(dois, 1):
        print(f"  [{i}] {doi}")

    print(f"\n🚀 开始下载...")
    print("=" * 70)

    downloader = MultiSourceDownloader(max_workers=1, max_retries=1)

    results = {"success": [], "failed": []}

    start_time = time.time()

    for i, doi in enumerate(dois, 1):
        print(f"\n[{i}/{len(dois)}] {doi}")
        print("-" * 70)

        # 只尝试 Unpaywall 和 Sci-Hub（快速测试）
        sources = [
            ("Unpaywall API", downloader._try_unpaywall),
            ("Sci-Hub ⚠️", downloader._try_scihub),
        ]

        success = False

        for source_name, download_func in sources:
            try:
                proxies = downloader.get_proxy_config(
                    use_china_network=(source_name == "Sci-Hub ⚠️")
                )

                print(f"[{source_name}] ...", end=" ")
                result = download_func(doi, proxies=proxies)

                if result and result.get("success"):
                    print(f"✅ 成功")
                    results["success"].append(
                        {
                            "doi": doi,
                            "source": source_name,
                            "file": result.get("file"),
                        }
                    )
                    success = True
                    break
                else:
                    print(f"❌ 失败")

                time.sleep(1)

            except Exception as e:
                print(f"❌ 错误: {str(e)[:50]}")

        if not success:
            print(f"❌ {doi} 所有来源均失败")
            results["failed"].append(doi)

        time.sleep(2)

    elapsed_time = time.time() - start_time

    print("\n" + "=" * 70)
    print(f"✅ 下载完成! 总耗时: {elapsed_time:.1f} 秒 ({elapsed_time / 60:.1f} 分钟)")
    print("=" * 70)

    # 打印总结
    print(f"\n📊 统计:")
    print(f"  总数: {len(dois)}")
    print(f"  成功: {len(results['success'])}")
    print(f"  失败: {len(results['failed'])}")

    success_rate = len(results["success"]) / len(dois) * 100
    print(f"  成功率: {success_rate:.1f}%")

    if results["success"]:
        print(f"\n✅ 成功列表:")
        for item in results["success"]:
            print(f"  ✓ {item['doi']}")
            print(f"    来源: {item['source']}")
            print(f"    文件: {item['file']}")

    if results["failed"]:
        print(f"\n❌ 失败列表:")
        for doi in results["failed"]:
            print(f"  ✗ {doi}")

    # 查看下载的文件
    print(f"\n📁 已下载的 PDF 文件:")
    pdf_files = [f for f in os.listdir("ris_downloads") if f.endswith(".pdf")]
    for i, filename in enumerate(sorted(pdf_files), 1):
        filepath = os.path.join("ris_downloads", filename)
        file_size = os.path.getsize(filepath)
        print(f"  [{i}] {filename} ({file_size:,} bytes)")

    print(f"\n总计: {len(pdf_files)} 个 PDF 文件")
    print("=" * 70)


if __name__ == "__main__":
    ris_file = "../savedrecs.ris"

    if len(sys.argv) > 1:
        ris_file = sys.argv[1]

    simple_batch_download(ris_file)
