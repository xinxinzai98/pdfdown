#!/usr/bin/env python3
"""多渠道 PDF 下载工具 - 从多个来源自动下载论文 PDF"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.sources.multi_channel_browser import MultiChannelBrowserDownloader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="多渠道 PDF 下载器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从所有渠道下载
  python3 multi_channel_download.py 10.1021/acsami.1c08462
  
  # 只从开放获取渠道下载
  python3 multi_channel_download.py 10.1021/acsami.1c08462 -s unpaywall semantic_scholar
  
  # 交互模式（用于 Sci-Hub 验证）
  python3 multi_channel_download.py 10.1021/acsami.1c08462 -i --wait 60
""",
    )
    parser.add_argument("doi", nargs="?", help="要下载的论文 DOI")
    parser.add_argument(
        "--sources",
        "-s",
        nargs="+",
        default=["unpaywall", "semantic_scholar", "scihub"],
        help="下载源: unpaywall, semantic_scholar, google_scholar, researchgate, scihub",
    )
    parser.add_argument("--output", "-o", default="./downloads", help="输出目录")
    parser.add_argument("--proxy", help="代理服务器 (如 http://127.0.0.1:7897)")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="交互模式（显示浏览器窗口）"
    )
    parser.add_argument("--wait", type=int, default=30, help="交互模式等待时间（秒）")
    parser.add_argument("--list-sources", action="store_true", help="列出所有下载源")

    args = parser.parse_args()

    if args.list_sources:
        print("\n可用下载源:")
        print("-" * 50)
        for source_id, info in MultiChannelBrowserDownloader.DOWNLOAD_SOURCES.items():
            legal_status = "✅ 合法" if info["legal"] else "⚠️ 非官方"
            print(f"  {source_id:20s} - {info['name']:25s} {legal_status}")
        print()
        return

    if not args.doi:
        parser.error(
            "请指定 DOI，例如: python3 multi_channel_download.py 10.1021/acsami.1c08462"
        )

    proxy = args.proxy or os.environ.get("HTTP_PROXY") or "http://127.0.0.1:7897"

    print(f"""
╔════════════════════════════════════════════════════╗
║       多渠道 PDF 下载器 v1.0                       ║
╠════════════════════════════════════════════════════╣
║  DOI: {args.doi:<43}║
║  来源: {str(args.sources):<42}║
║  输出: {args.output:<42}║
║  代理: {proxy:<42}║
║  交互: {str(args.interactive):<42}║
╚════════════════════════════════════════════════════╝
""")

    downloader = MultiChannelBrowserDownloader(
        proxy=proxy, headless=not args.interactive, download_dir=args.output
    )

    try:
        result = await downloader.download(
            args.doi,
            sources=args.sources,
            interactive=args.interactive,
            wait_time=args.wait,
        )

        print("\n" + "=" * 60)
        if result["success"]:
            print(f"✅ 下载成功!")
            print(f"   文件: {result['file']}")
            print(f"   来源: {result['source']}")
        else:
            print("❌ 所有来源均未能下载")
            print("\n尝试过的来源:")
            for attempt in result["attempts"]:
                status = "✅" if attempt["success"] else "❌"
                error = attempt.get("error", "")
                print(
                    f"   {status} {attempt['source']}: {error[:50] if error else '失败'}"
                )
        print("=" * 60)

    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())
