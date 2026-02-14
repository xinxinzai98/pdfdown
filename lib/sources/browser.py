"""浏览器自动化下载源 (用于动态加载页面)"""

import asyncio
import logging
import os
import re
import tempfile
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright 未安装，浏览器下载功能不可用")


class BrowserDownloader:
    """浏览器自动化下载器"""

    def __init__(self, proxy: Optional[str] = None, headless: bool = True):
        self.proxy = (
            proxy or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        )
        self.headless = headless
        self.browser = None
        self.playwright = None

    async def init_browser(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装")

        if self.browser:
            return

        self.playwright = await async_playwright().start()

        launch_options = {"headless": self.headless}
        if self.proxy:
            launch_options["proxy"] = {"server": self.proxy}

        self.browser = await self.playwright.chromium.launch(**launch_options)
        logger.info(f"浏览器已启动 (headless={self.headless})")

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def download_from_scihub(
        self, doi: str, interactive: bool = False, wait_time: int = 30
    ) -> Optional[Dict[str, Any]]:
        """使用浏览器从 Sci-Hub 下载

        Args:
            doi: 论文 DOI
            interactive: 是否使用交互模式（显示浏览器窗口）
            wait_time: 交互模式下的等待时间（秒）
        """
        if not PLAYWRIGHT_AVAILABLE:
            return None

        # 交互模式强制显示窗口
        if interactive:
            if self.browser:
                await self.browser.close()
                self.browser = None
            self.headless = False

        await self.init_browser()

        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        mirrors = [
            "https://sci-hub.se",
            "https://sci-hub.st",
            "https://sci-hub.ru",
            "https://sci-hub.do",
            "https://sci-hub.wf",
        ]

        pdf_url = None

        for mirror in mirrors:
            url = f"{mirror}/{doi}"
            logger.info(f"浏览器访问: {url}")

            if interactive:
                logger.info(
                    f"⏳ 请在浏览器窗口中完成验证（如有），系统将自动检测 PDF..."
                )

            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")

                if interactive:
                    # 交互模式：持续检查直到找到 PDF 或超时
                    for i in range(wait_time):
                        await asyncio.sleep(1)

                        embed = await page.query_selector("embed[src]")
                        if embed:
                            src = await embed.get_attribute("src")
                            if src and (
                                ".pdf" in src.lower() or src.startswith("http")
                            ):
                                if src.startswith("//"):
                                    src = "https:" + src
                                pdf_url = src
                                logger.info(f"✅ 检测到 PDF!")
                                break

                        # 也检查 iframe
                        iframe = await page.query_selector("iframe[src]")
                        if iframe:
                            src = await iframe.get_attribute("src")
                            if (
                                src
                                and "blueridge" not in src.lower()
                                and "ads" not in src.lower()
                            ):
                                if src.startswith("//"):
                                    src = "https:" + src
                                if ".pdf" in src.lower():
                                    pdf_url = src
                                    logger.info(f"✅ 检测到 PDF (iframe)!")
                                    break

                        if i % 5 == 0:
                            logger.info(f"等待中... ({i}/{wait_time}s)")
                else:
                    # 自动模式：等待一段时间后检查
                    for _ in range(10):
                        title = await page.title()
                        if "DDoS" not in title and "DDOS" not in title:
                            break
                        await asyncio.sleep(2)

                    await asyncio.sleep(2)

                    embed = await page.query_selector("embed[src]")
                    if embed:
                        src = await embed.get_attribute("src")
                        if src and (".pdf" in src.lower() or src.startswith("http")):
                            if src.startswith("//"):
                                src = "https:" + src
                            pdf_url = src
                            logger.info(f"找到 PDF: {pdf_url[:80]}...")
                            break

                    # 检查页面内容中的 PDF 链接
                    content = await page.content()
                    pdf_match = re.search(
                        r'(https?://[^"\'>\s]+\.pdf[^"\'>\s]*)', content, re.I
                    )
                    if pdf_match:
                        pdf_url = pdf_match.group(1)
                        logger.info(f"找到 PDF (regex): {pdf_url[:80]}...")
                        break

            except Exception as e:
                logger.debug(f"镜像 {mirror} 失败: {str(e)[:50]}")
                continue

            if pdf_url:
                break

        await context.close()

        if pdf_url:
            return {"success": True, "pdf_url": pdf_url, "source": "Sci-Hub-Browser"}

        return None

    def download_sync(
        self, doi: str, interactive: bool = False, wait_time: int = 30
    ) -> Optional[Dict[str, Any]]:
        """同步下载接口"""
        if not PLAYWRIGHT_AVAILABLE:
            return None

        async def _download():
            try:
                return await self.download_from_scihub(
                    doi, interactive=interactive, wait_time=wait_time
                )
            finally:
                await self.close()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _download())
                return future.result(timeout=120)
        else:
            return loop.run_until_complete(_download())


def check_browser_available() -> bool:
    """检查浏览器下载功能是否可用"""
    return PLAYWRIGHT_AVAILABLE
