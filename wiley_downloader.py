#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wiley 论文下载器 - 通过 CDP 连接已登录的 Edge 浏览器

使用步骤：
1. 启动干净 Edge（不带代理）：
   open -na "Microsoft Edge" --args \
     --remote-debugging-port=9222 \
     --user-data-dir=/tmp/edge-cdp-profile-wiley \
     --no-proxy-server \
     --no-first-run --no-default-browser-check

2. 在 Edge 中手动登录 Wiley（通过机构登录）

3. 运行此脚本下载论文
"""

import asyncio
import logging
import os
import re
import sys
from typing import Optional, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.error(
        "请安装 Playwright: pip install playwright && playwright install chromium"
    )


def sanitize_filename(name: str, max_len: int = 180) -> str:
    """清理文件名，移除非法字符"""
    # 替换非法字符
    name = re.sub(r'[/\\:*?"<>|]', "_", name)
    # 移除多余空格
    name = re.sub(r"\s+", " ", name).strip()
    # 截断长度
    if len(name) > max_len:
        name = name[:max_len]
    return name


class WileyDownloader:
    """Wiley 论文下载器 - 通过 CDP 复用已登录浏览器"""

    CDP_URL = "http://127.0.0.1:9222"
    WILEY_PDFDIRECT_TEMPLATE = (
        "https://advanced.onlinelibrary.wiley.com/doi/pdfdirect/{doi}"
    )
    WILEY_FULL_TEMPLATE = "https://advanced.onlinelibrary.wiley.com/doi/full/{doi}"

    def __init__(self, download_dir: str = "./wiley_downloads"):
        self.download_dir = download_dir
        self.browser = None
        self.context = None
        self.playwright = None

        os.makedirs(download_dir, exist_ok=True)

    async def connect(self) -> bool:
        """连接到已打开的 Edge 浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright 未安装")
            return False

        try:
            self.playwright = await async_playwright().start()

            logger.info(f"正在连接 Edge 浏览器: {self.CDP_URL}")
            self.browser = await self.playwright.chromium.connect_over_cdp(self.CDP_URL)

            # 获取现有 context（包含登录 cookie）
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                logger.info(f"✅ 已连接到 Edge，复用现有登录上下文")
                return True
            else:
                logger.error("未找到浏览器上下文")
                return False

        except Exception as e:
            logger.error(f"连接失败: {e}")
            logger.error("请确保 Edge 已启动并开启调试端口:")
            logger.error(
                '  open -na "Microsoft Edge" --args --remote-debugging-port=9222 --user-data-dir=/tmp/edge-cdp-profile-wiley --no-proxy-server'
            )
            return False

    async def close(self):
        """断开连接（不关闭浏览器）"""
        # 注意：不关闭 browser，只断开连接
        self.context = None
        self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def download_wiley(
        self, doi: str, metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """从 Wiley 下载 PDF - 使用网络拦截获取实际 PDF 响应"""

        if not self.context:
            logger.error("未连接到浏览器，请先调用 connect()")
            return None

        pdf_url = self.WILEY_PDFDIRECT_TEMPLATE.format(doi=doi)
        pdf_data_holder = {"data": None}

        pages = self.context.pages
        if pages:
            page = pages[-1]
        else:
            page = await self.context.new_page()

        async def capture_pdf_response(route, request):
            nonlocal pdf_data_holder
            response = await route.fetch()
            body = await response.body()

            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type.lower() or body[:4] == b"%PDF":
                logger.info(f"[Wiley] 拦截到 PDF 响应: {len(body):,} bytes")
                pdf_data_holder["data"] = body

            await route.fulfill(response=response)

        try:
            logger.info(f"[Wiley] 下载 PDF: {pdf_url}")

            await page.route("**/*", capture_pdf_response)

            response = await page.goto(pdf_url, timeout=60000)

            if not response:
                logger.error("[Wiley] 无响应")
                return None

            logger.info(f"[Wiley] Response status: {response.status}")

            await asyncio.sleep(2)
            await page.wait_for_load_state("networkidle", timeout=30000)

            pdf_data = pdf_data_holder["data"]

            if not pdf_data:
                initial_body = await response.body()
                if initial_body[:4] == b"%PDF":
                    pdf_data = initial_body
                    logger.info(f"[Wiley] 从初始响应获取 PDF: {len(pdf_data):,} bytes")

            if not pdf_data:
                logger.info("[Wiley] 尝试等待 embed 加载...")
                for i in range(10):
                    await asyncio.sleep(1)
                    if pdf_data_holder["data"]:
                        pdf_data = pdf_data_holder["data"]
                        break

            if not pdf_data:
                await page.unroute("**/*", capture_pdf_response)
                await page.route("**/*.pdf**", capture_pdf_response)

                logger.info("[Wiley] 尝试直接访问 PDF URL...")
                pdf_response = await page.goto(
                    pdf_url, wait_until="networkidle", timeout=60000
                )
                if pdf_response:
                    body = await pdf_response.body()
                    if body[:4] == b"%PDF":
                        pdf_data = body

            if not pdf_data:
                embed = await page.query_selector("embed[type='application/pdf']")
                if embed:
                    src = await embed.get_attribute("src")
                    logger.info(f"[Wiley] embed src: {src}")

                    if src and src != "about:blank":
                        if src.startswith("//"):
                            src = "https:" + src
                        logger.info(f"[Wiley] 尝试从 embed src 获取: {src[:80]}...")
                        try:
                            pdf_response = await self.context.request.get(src)
                            if pdf_response.status == 200:
                                pdf_data = await pdf_response.body()
                                if pdf_data[:4] == b"%PDF":
                                    logger.info(
                                        f"[Wiley] 从 embed 获取成功: {len(pdf_data):,} bytes"
                                    )
                        except Exception as e:
                            logger.warning(f"[Wiley] embed 获取失败: {e}")

            try:
                await page.unroute("**/*", capture_pdf_response)
            except:
                pass

            if not pdf_data or pdf_data[:4] != b"%PDF":
                logger.error(
                    f"[Wiley] 无法获取有效 PDF (size={len(pdf_data) if pdf_data else 0})"
                )
                return None

            logger.info(f"[Wiley] 获取到有效 PDF: {len(pdf_data):,} bytes")

            if metadata:
                author = metadata.get("first_author", "Unknown")
                year = metadata.get("year", "")
                title = metadata.get("title", "Untitled")[:50]
                doi_safe = doi.replace("/", "_")
                filename = f"{author}_{year}_{title}_{doi_safe}.pdf"
                filename = sanitize_filename(filename)
            else:
                filename = f"wiley_{doi.replace('/', '_')}.pdf"

            filepath = os.path.join(self.download_dir, filename)
            with open(filepath, "wb") as f:
                f.write(pdf_data)
            logger.info(f"✅ [Wiley] 下载成功: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"[Wiley] 下载失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def batch_download(
        self, dois: List[str], metadata_list: Optional[List[Dict]] = None
    ) -> Dict:
        """批量下载

        Args:
            dois: DOI 列表
            metadata_list: 元数据列表（可选）

        Returns:
            下载结果统计
        """
        results = {
            "total": len(dois),
            "success": 0,
            "failed": 0,
            "files": [],
            "errors": [],
        }

        for i, doi in enumerate(dois, 1):
            logger.info(f"\n{'=' * 60}")
            logger.info(f"[{i}/{len(dois)}] DOI: {doi}")
            logger.info(f"{'=' * 60}")

            metadata = (
                metadata_list[i - 1]
                if metadata_list and i <= len(metadata_list)
                else None
            )

            filepath = await self.download_wiley(doi, metadata)

            if filepath:
                results["success"] += 1
                results["files"].append({"doi": doi, "file": filepath})
            else:
                results["failed"] += 1
                results["errors"].append(doi)

            # 避免请求过快
            await asyncio.sleep(1)

        return results


class SciHubDownloader:
    """Sci-Hub 下载器 - 需要走代理"""

    def __init__(
        self,
        proxy: str = "http://127.0.0.1:7897",
        download_dir: str = "./scihub_downloads",
    ):
        self.proxy = proxy
        self.download_dir = download_dir
        self.browser = None
        self.context = None
        self.playwright = None

        os.makedirs(download_dir, exist_ok=True)

    async def init(self):
        """初始化浏览器（带代理）"""
        if not PLAYWRIGHT_AVAILABLE:
            return False

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # Sci-Hub 可能需要手动验证
            proxy={"server": self.proxy},
        )
        self.context = await self.browser.new_context()
        logger.info(f"[Sci-Hub] 浏览器已启动（代理: {self.proxy}）")
        return True

    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def download(self, doi: str, wait_time: int = 30) -> Optional[str]:
        """从 Sci-Hub 下载"""
        if not self.context:
            await self.init()

        page = await self.context.new_page()

        mirrors = [
            "https://sci-hub.se",
            "https://sci-hub.st",
            "https://sci-hub.ru",
            "https://sci-hub.do",
        ]

        try:
            for mirror in mirrors:
                url = f"{mirror}/{doi}"
                logger.info(f"[Sci-Hub] 尝试: {url}")

                try:
                    await page.goto(url, timeout=30000)

                    # 等待页面加载
                    for i in range(wait_time):
                        await asyncio.sleep(1)

                        # 查找 embed
                        embed = await page.query_selector("embed[src]")
                        if embed:
                            src = await embed.get_attribute("src")
                            if src and ("pdf" in src.lower() or src.startswith("http")):
                                if src.startswith("//"):
                                    src = "https:" + src

                                # 下载 PDF
                                logger.info(f"[Sci-Hub] 找到 PDF: {src[:80]}...")
                                response = await self.context.request.get(src)

                                if response.status == 200:
                                    pdf_data = await response.body()
                                    filename = f"scihub_{doi.replace('/', '_')}.pdf"
                                    filepath = os.path.join(self.download_dir, filename)

                                    with open(filepath, "wb") as f:
                                        f.write(pdf_data)

                                    logger.info(f"✅ [Sci-Hub] 下载成功: {filepath}")
                                    return filepath

                        if i % 5 == 0:
                            logger.info(f"[Sci-Hub] 等待中... ({i}/{wait_time}s)")

                except Exception as e:
                    logger.debug(f"[Sci-Hub] {mirror} 失败: {str(e)[:30]}")

            logger.warning(f"[Sci-Hub] 所有镜像均失败: {doi}")
            return None

        finally:
            await page.close()


def parse_ris_file(ris_path: str) -> List[Dict]:
    """解析 RIS 文件"""
    papers = []
    current = {}

    with open(ris_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith("TY  -"):
                if current.get("doi"):
                    papers.append(current)
                current = {}
            elif line.startswith("DO  -"):
                current["doi"] = line[5:].strip()
            elif line.startswith("TI  -"):
                current["title"] = line[5:].strip()
            elif line.startswith("AU  -"):
                if "authors" not in current:
                    current["authors"] = []
                current["authors"].append(line[5:].strip())
            elif line.startswith("PY  -"):
                current["year"] = line[5:].strip()[:4]

        if current.get("doi"):
            papers.append(current)

    # 提取第一作者
    for paper in papers:
        if paper.get("authors"):
            paper["first_author"] = paper["authors"][0].split(",")[0]
        else:
            paper["first_author"] = "Unknown"

    return papers


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Wiley/Sci-Hub 论文下载器")
    parser.add_argument("input", help="DOI 或 RIS 文件路径")
    parser.add_argument(
        "--source", choices=["wiley", "scihub"], default="wiley", help="下载源"
    )
    parser.add_argument("--output", "-o", default="./downloads", help="输出目录")
    parser.add_argument("--proxy", default="http://127.0.0.1:7897", help="Sci-Hub 代理")
    parser.add_argument("--wait", type=int, default=30, help="Sci-Hub 等待时间")

    args = parser.parse_args()

    # 判断是 DOI 还是文件
    if os.path.exists(args.input):
        papers = parse_ris_file(args.input)
        dois = [p["doi"] for p in papers]
        logger.info(f"📋 从 RIS 文件解析到 {len(dois)} 篇论文")
    else:
        dois = [args.input]
        papers = [{"doi": args.input}]

    if args.source == "wiley":
        print(f"""
╔════════════════════════════════════════════════════╗
║     Wiley 论文下载器 (CDP 模式)                     ║
╠════════════════════════════════════════════════════╣
║  请确保 Edge 浏览器已启动并登录 Wiley:             ║
║                                                    ║
║  open -na "Microsoft Edge" --args \\               ║
║    --remote-debugging-port=9222 \\                  ║
║    --user-data-dir=/tmp/edge-cdp-profile-wiley \\   ║
║    --no-proxy-server \\                             ║
║    --no-first-run --no-default-browser-check       ║
╚════════════════════════════════════════════════════╝
""")

        downloader = WileyDownloader(download_dir=args.output)

        if not await downloader.connect():
            sys.exit(1)

        try:
            results = await downloader.batch_download(dois, papers)

            print(f"\n{'=' * 60}")
            print(f"📊 下载完成")
            print(f"{'=' * 60}")
            print(f"✅ 成功: {results['success']}/{results['total']}")
            print(f"❌ 失败: {results['failed']}/{results['total']}")

            if results["files"]:
                print("\n成功列表:")
                for item in results["files"]:
                    print(f"  ✓ {item['doi']}")
                    print(f"    {item['file']}")

        finally:
            await downloader.close()

    elif args.source == "scihub":
        print(f"""
╔════════════════════════════════════════════════════╗
║     Sci-Hub 论文下载器                              ║
╠════════════════════════════════════════════════════╣
║  代理: {args.proxy:<42}║
║  等待时间: {args.wait}s                                   ║
╚════════════════════════════════════════════════════╝
""")

        downloader = SciHubDownloader(proxy=args.proxy, download_dir=args.output)

        try:
            for doi in dois:
                await downloader.download(doi, wait_time=args.wait)
        finally:
            await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())
