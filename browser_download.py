#!/usr/bin/env python3
"""浏览器下载工具 - 使用 Playwright 下载动态加载的 PDF"""

import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.sources.browser import BrowserDownloader, check_browser_available

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="浏览器 PDF 下载工具")
    parser.add_argument("doi", help="要下载的论文 DOI")
    parser.add_argument("--source", choices=["scihub"], default="scihub", help="下载源")
    parser.add_argument("--proxy", help="代理服务器 (如 http://127.0.0.1:7897)")
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="交互模式（显示浏览器窗口，手动通过验证）",
    )
    parser.add_argument("--wait", type=int, default=30, help="交互模式等待时间（秒）")
    parser.add_argument("--output", "-o", help="输出目录")

    args = parser.parse_args()

    if not check_browser_available():
        logger.error("Playwright 未安装!")
        logger.error("请运行: pip install playwright && playwright install chromium")
        sys.exit(1)

    proxy = args.proxy or os.environ.get("HTTP_PROXY") or "http://127.0.0.1:7897"

    logger.info(f"DOI: {args.doi}")
    logger.info(f"下载源: {args.source}")
    logger.info(f"代理: {proxy}")
    logger.info(f"交互模式: {args.interactive}")

    async def download():
        downloader = BrowserDownloader(proxy=proxy, headless=not args.interactive)

        try:
            result = await downloader.download_from_scihub(
                args.doi, interactive=args.interactive, wait_time=args.wait
            )

            if result and result.get("success"):
                pdf_url = result.get("pdf_url")

                if pdf_url:
                    logger.info(f"✅ 找到 PDF URL: {pdf_url}")

                    import requests

                    response = requests.get(
                        pdf_url,
                        timeout=60,
                        stream=True,
                        proxies={"http": proxy, "https": proxy},
                        headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                        },
                    )

                    if response.status_code == 200:
                        filename = args.doi.replace("/", "_") + ".pdf"
                        if args.output:
                            os.makedirs(args.output, exist_ok=True)
                            filepath = os.path.join(args.output, filename)
                        else:
                            filepath = filename

                        with open(filepath, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)

                        logger.info(
                            f"✅ 下载完成: {filepath} ({os.path.getsize(filepath):,} bytes)"
                        )
                        return filepath
                    else:
                        logger.error(f"下载失败: HTTP {response.status_code}")
            else:
                logger.error("❌ 下载失败")
                return None

        finally:
            await downloader.close()

    try:
        result = asyncio.run(download())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(1)


if __name__ == "__main__":
    main()
