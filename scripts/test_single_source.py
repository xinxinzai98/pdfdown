#!/usr/bin/env python3
"""
测试单个下载源
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from multi_source_ris_downloader_v3 import MultiSourceDownloader


def test_single_source(doi, source_name):
    """测试单个下载源"""

    downloader = MultiSourceDownloader(max_workers=1, max_retries=1)

    source_map = {
        "unpaywall": downloader._try_unpaywall,
        "scihub": downloader._try_scihub,
        "semantic": downloader._try_semantic_scholar,
        "core": downloader._try_core,
    }

    if source_name not in source_map:
        print(f"Unknown source: {source_name}")
        return

    func = source_map[source_name]

    print("=" * 70)
    print(f"🧪 测试 {source_name.upper()} 下载源")
    print(f"DOI: {doi}")
    print("=" * 70)

    import time

    start = time.time()

    try:
        proxies = downloader.get_proxy_config(
            use_china_network=(source_name == "scihub")
        )
        print(f"使用代理: {'否' if source_name == 'scihub' else '是'}")

        result = func(doi, proxies=proxies)

        elapsed = time.time() - start

        if result and result.get("success"):
            print(f"\n✅ 成功! (耗时: {elapsed:.2f}s)")
            print(f"文件: {result.get('file')}")
            print(f"大小: {result.get('size', 0):,} bytes")
        else:
            print(f"\n❌ 失败 (耗时: {elapsed:.2f}s)")
            if result and "error" in result:
                print(f"错误: {result['error']}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n❌ 异常 (耗时: {elapsed:.2f}s)")
        print(f"错误: {e}")
        import traceback

        traceback.print_exc()

    print("=" * 70)


if __name__ == "__main__":
    doi = "10.1016/j.apenergy.2025.126643"
    source = "unpaywall"

    if len(sys.argv) > 1:
        doi = sys.argv[1]
    if len(sys.argv) > 2:
        source = sys.argv[2]

    test_single_source(doi, source)
