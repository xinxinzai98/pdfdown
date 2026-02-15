"""多渠道浏览器下载器 - 从多个来源自动下载 PDF"""

import asyncio
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class MultiChannelBrowserDownloader:
    """多渠道浏览器下载器"""

    DOWNLOAD_SOURCES = {
        "unpaywall": {
            "name": "Unpaywall (开放获取)",
            "legal": True,
        },
        "google_scholar": {
            "name": "Google Scholar",
            "legal": True,
        },
        "researchgate": {
            "name": "ResearchGate",
            "legal": True,
        },
        "semantic_scholar": {
            "name": "Semantic Scholar",
            "legal": True,
        },
        "core": {
            "name": "CORE",
            "legal": True,
        },
        "scihub": {
            "name": "Sci-Hub",
            "legal": False,
        },
    }

    def __init__(
        self,
        proxy: Optional[str] = None,
        headless: bool = True,
        download_dir: str = "./downloads",
    ):
        self.proxy = proxy or os.environ.get("HTTP_PROXY")
        self.headless = headless
        self.download_dir = download_dir
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None

        os.makedirs(download_dir, exist_ok=True)

    async def init(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright 未安装，请运行: pip install playwright && playwright install chromium"
            )

        if self.browser:
            return

        self.playwright = await async_playwright().start()

        launch_options = {"headless": self.headless}
        if self.proxy:
            launch_options["proxy"] = {"server": self.proxy}

        self.browser = await self.playwright.chromium.launch(**launch_options)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            viewport={"width": 1280, "height": 900},
            accept_downloads=True,
        )

        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        logger.info(f"浏览器已启动 (headless={self.headless})")

    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def _download_pdf_from_url(
        self, page: Page, pdf_url: str, filename: str
    ) -> Optional[str]:
        """从 URL 下载 PDF"""
        try:
            logger.info(f"下载 PDF: {pdf_url[:80]}...")

            async with page.expect_download(timeout=60000) as download_info:
                try:
                    await page.goto(pdf_url, timeout=30000)
                    await asyncio.sleep(1)
                except:
                    pass

            try:
                download = await download_info.value
                if download:
                    suggested_name = download.suggested_filename or filename
                    if not suggested_name.endswith(".pdf"):
                        suggested_name += ".pdf"

                    save_path = os.path.join(self.download_dir, suggested_name)
                    await download.save_as(save_path)
                    logger.info(f"✅ 下载成功: {save_path}")
                    return save_path
            except asyncio.TimeoutError:
                pass

            current_url = page.url
            if ".pdf" in current_url:
                logger.info(f"当前页面是 PDF: {current_url}")
                return current_url

        except Exception as e:
            logger.debug(f"PDF 下载失败: {str(e)[:50]}")

        return None

    async def download_from_unpaywall(self, doi: str) -> Optional[str]:
        """从 Unpaywall 获取开放获取 PDF"""
        page = await self.context.new_page()

        try:
            api_url = f"https://api.unpaywall.org/v2/{doi}?email=test@example.com"
            logger.info(f"[Unpaywall] 查询 DOI: {doi}")

            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=15) as resp:
                    if resp.status != 200:
                        logger.debug(f"[Unpaywall] API 返回 {resp.status}")
                        return None
                    data = await resp.json()

            if not data.get("is_oa"):
                logger.info("[Unpaywall] 无开放获取版本")
                return None

            oa_location = data.get("best_oa_location") or {}
            pdf_url = oa_location.get("url_for_pdf") or oa_location.get("url")

            if not pdf_url:
                logger.debug("[Unpaywall] 未找到 PDF URL")
                return None

            logger.info(f"[Unpaywall] 找到 OA 链接: {pdf_url}")

            # 用浏览器访问 PDF 链接
            await page.goto(pdf_url, timeout=30000, wait_until="networkidle")
            await asyncio.sleep(3)

            # 检查当前 URL 是否已经是 PDF
            current_url = page.url
            if ".pdf" in current_url:
                logger.info(f"[Unpaywall] 页面直接是 PDF")
                # 直接下载 PDF
                filename = f"unpaywall_{doi.replace('/', '_')}.pdf"
                save_path = os.path.join(self.download_dir, filename)

                # 使用页面的 PDF 保存功能
                pdf_data = await page.pdf()
                with open(save_path, "wb") as f:
                    f.write(pdf_data)
                logger.info(f"✅ [Unpaywall] 下载成功: {save_path}")
                return save_path

            # 尝试点击下载按钮
            download_selectors = [
                "a[href*='download']",
                "a[href*='.pdf']",
                "button:has-text('Download')",
                "a:has-text('PDF')",
                "a:has-text('Download PDF')",
                ".download-link",
                "#downloadPdf",
                "a[download]",
                ".pdf-download",
                "a[href*='getpdf']",
            ]

            for selector in download_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements[:3]:
                        try:
                            # 检查元素是否可见
                            is_visible = await element.is_visible()
                            if not is_visible:
                                continue

                            href = await element.get_attribute("href")
                            if href and ".pdf" in href.lower():
                                logger.info(f"[Unpaywall] 找到 PDF 链接: {href}")

                                # 尝试下载
                                async with page.expect_download(
                                    timeout=30000
                                ) as download_info:
                                    await element.click()
                                    download = await download_info.value

                                    filename = f"unpaywall_{doi.replace('/', '_')}.pdf"
                                    save_path = os.path.join(
                                        self.download_dir, filename
                                    )
                                    await download.save_as(save_path)
                                    logger.info(f"✅ [Unpaywall] 下载成功: {save_path}")
                                    return save_path
                        except Exception as e:
                            logger.debug(f"[Unpaywall] 点击下载失败: {str(e)[:30]}")
                            continue
                except:
                    continue

            # 尝试直接从页面 URL 下载
            content_type = await page.evaluate("document.contentType")
            if content_type and "pdf" in content_type:
                filename = f"unpaywall_{doi.replace('/', '_')}.pdf"
                save_path = os.path.join(self.download_dir, filename)
                pdf_data = await page.pdf()
                with open(save_path, "wb") as f:
                    f.write(pdf_data)
                logger.info(f"✅ [Unpaywall] PDF 下载成功: {save_path}")
                return save_path

            logger.debug("[Unpaywall] 无法找到下载方式")
            return None

        except Exception as e:
            logger.debug(f"[Unpaywall] 下载失败: {str(e)[:50]}")
            return None
        finally:
            await page.close()

    async def download_from_google_scholar(self, doi: str) -> Optional[str]:
        """从 Google Scholar 搜索并下载"""
        page = await self.context.new_page()

        try:
            search_url = f"https://scholar.google.com/scholar?q={doi}"
            logger.info(f"[Google Scholar] 搜索: {doi}")

            await page.goto(search_url, timeout=30000)
            await asyncio.sleep(2)

            pdf_links = await page.query_selector_all(
                "a[href*='.pdf'], a:has-text('PDF')"
            )

            for link in pdf_links[:3]:
                try:
                    href = await link.get_attribute("href")
                    if href and ".pdf" in href.lower():
                        logger.info(f"[Google Scholar] 找到 PDF 链接: {href[:80]}")

                        filename = f"gs_{doi.replace('/', '_')}.pdf"
                        result = await self._download_pdf_from_url(page, href, filename)
                        if result:
                            return result
                except:
                    continue

            return None

        except Exception as e:
            logger.debug(f"[Google Scholar] 下载失败: {str(e)[:50]}")
            return None
        finally:
            await page.close()

    async def download_from_researchgate(self, doi: str) -> Optional[str]:
        """从 ResearchGate 下载"""
        page = await self.context.new_page()

        try:
            search_url = f"https://www.researchgate.net/search?q={doi}"
            logger.info(f"[ResearchGate] 搜索: {doi}")

            await page.goto(search_url, timeout=30000)
            await asyncio.sleep(2)

            download_btn = await page.query_selector(
                "a[href*='download'], button:has-text('Download'), .nova-legacy-c-button--color-blue"
            )

            if download_btn:
                try:
                    async with page.expect_download(timeout=60000) as download_info:
                        await download_btn.click()
                        download = await download_info.value

                        filename = f"rg_{doi.replace('/', '_')}.pdf"
                        save_path = os.path.join(self.download_dir, filename)
                        await download.save_as(save_path)
                        logger.info(f"✅ [ResearchGate] 下载成功: {save_path}")
                        return save_path
                except:
                    pass

            return None

        except Exception as e:
            logger.debug(f"[ResearchGate] 下载失败: {str(e)[:50]}")
            return None
        finally:
            await page.close()

    async def download_from_semantic_scholar(self, doi: str) -> Optional[str]:
        """从 Semantic Scholar 下载"""
        page = await self.context.new_page()

        try:
            api_url = f"https://api.semanticscholar.org/v1/paper/DOI:{doi}"
            logger.info(f"[Semantic Scholar] 查询: {doi}")

            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=15) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()

            oa_pdf = data.get("openAccessPdf")
            if not oa_pdf:
                logger.debug("[Semantic Scholar] 无开放获取 PDF")
                return None

            pdf_url = oa_pdf.get("url")
            if not pdf_url:
                return None

            logger.info(f"[Semantic Scholar] 找到 PDF: {pdf_url}")

            filename = f"ss_{doi.replace('/', '_')}.pdf"
            result = await self._download_pdf_from_url(page, pdf_url, filename)
            return result

        except Exception as e:
            logger.debug(f"[Semantic Scholar] 下载失败: {str(e)[:50]}")
            return None
        finally:
            await page.close()

    async def download_from_scihub(
        self, doi: str, interactive: bool = False, wait_time: int = 30
    ) -> Optional[str]:
        """从 Sci-Hub 下载"""
        page = await self.context.new_page()

        mirrors = [
            "https://sci-hub.se",
            "https://sci-hub.st",
            "https://sci-hub.ru",
            "https://sci-hub.do",
            "https://sci-hub.wf",
        ]

        try:
            for mirror in mirrors:
                url = f"{mirror}/{doi}"
                logger.info(f"[Sci-Hub] 尝试: {url}")

                try:
                    await page.goto(url, timeout=30000)

                    if interactive:
                        logger.info(f"⏳ 请在浏览器中完成验证（{wait_time}秒）...")
                        for i in range(wait_time):
                            await asyncio.sleep(1)

                            embed = await page.query_selector("embed[src*='http']")
                            if embed:
                                src = await embed.get_attribute("src")
                                if src:
                                    if src.startswith("//"):
                                        src = "https:" + src
                                    logger.info(f"✅ [Sci-Hub] 找到 PDF!")
                                    filename = f"scihub_{doi.replace('/', '_')}.pdf"
                                    result = await self._download_pdf_from_url(
                                        page, src, filename
                                    )
                                    if result:
                                        return result
                    else:
                        await asyncio.sleep(5)

                        embed = await page.query_selector("embed[src*='http']")
                        if embed:
                            src = await embed.get_attribute("src")
                            if src:
                                if src.startswith("//"):
                                    src = "https:" + src
                                filename = f"scihub_{doi.replace('/', '_')}.pdf"
                                result = await self._download_pdf_from_url(
                                    page, src, filename
                                )
                                if result:
                                    return result

                except Exception as e:
                    logger.debug(f"[Sci-Hub] {mirror} 失败: {str(e)[:30]}")
                    continue

            return None

        finally:
            await page.close()

    async def download(
        self,
        doi: str,
        sources: Optional[List[str]] = None,
        interactive: bool = False,
        wait_time: int = 30,
    ) -> Dict[str, Any]:
        """尝试从多个渠道下载

        Args:
            doi: 论文 DOI
            sources: 要尝试的下载源列表，默认全部
            interactive: 是否使用交互模式（用于 Sci-Hub）
            wait_time: 交互模式等待时间

        Returns:
            下载结果字典
        """
        if sources is None:
            sources = [
                "unpaywall",
                "semantic_scholar",
                "google_scholar",
                "researchgate",
                "scihub",
            ]

        results = {
            "doi": doi,
            "success": False,
            "file": None,
            "source": None,
            "attempts": [],
        }

        await self.init()

        source_methods = {
            "unpaywall": self.download_from_unpaywall,
            "semantic_scholar": self.download_from_semantic_scholar,
            "google_scholar": self.download_from_google_scholar,
            "researchgate": self.download_from_researchgate,
            "scihub": lambda d: self.download_from_scihub(d, interactive, wait_time),
        }

        for source in sources:
            if source not in source_methods:
                continue

            source_info = self.DOWNLOAD_SOURCES.get(source, {})
            logger.info(f"\n{'=' * 50}")
            logger.info(f"尝试来源: {source_info.get('name', source)}")
            logger.info(f"{'=' * 50}")

            attempt = {"source": source, "success": False}

            try:
                result = await source_methods[source](doi)

                if result:
                    results["success"] = True
                    results["file"] = result
                    results["source"] = source
                    attempt["success"] = True
                    logger.info(
                        f"\n✅ 下载成功! 来源: {source_info.get('name', source)}"
                    )
                    break

            except Exception as e:
                attempt["error"] = str(e)[:100]
                logger.debug(f"来源 {source} 失败: {str(e)[:50]}")

            results["attempts"].append(attempt)

        if not results["success"]:
            logger.warning(f"\n❌ 所有来源均未能下载: {doi}")

        return results


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="多渠道浏览器 PDF 下载器")
    parser.add_argument("doi", help="要下载的论文 DOI")
    parser.add_argument(
        "--sources",
        "-s",
        nargs="+",
        default=["unpaywall", "semantic_scholar", "scihub"],
        help="下载源 (unpaywall, semantic_scholar, google_scholar, researchgate, scihub)",
    )
    parser.add_argument("--output", "-o", default="./downloads", help="输出目录")
    parser.add_argument("--proxy", help="代理服务器")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--wait", type=int, default=30, help="交互模式等待时间")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    downloader = MultiChannelBrowserDownloader(
        proxy=args.proxy, headless=not args.interactive, download_dir=args.output
    )

    try:
        result = await downloader.download(
            args.doi,
            sources=args.sources,
            interactive=args.interactive,
            wait_time=args.wait,
        )

        if result["success"]:
            print(f"\n✅ 下载成功: {result['file']}")
            print(f"   来源: {result['source']}")
        else:
            print(f"\n❌ 下载失败")

    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())
