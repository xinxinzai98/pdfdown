#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整下载流程: 公开渠道 -> 浏览器官方

第一阶段: 公开渠道 (Unpaywall + CORE)
第二阶段: 浏览器官方渠道 (Wiley, Elsevier, MDPI, ACS, Springer 等)

用法:
    python3 full_pipeline.py savedrecs.ris
    python3 full_pipeline.py savedrecs.ris -o ./downloads
    python3 full_pipeline.py savedrecs.ris --skip-public
"""

import asyncio
import logging
import os
import re
import sys
from typing import Dict, List, Optional, Set
from urllib.parse import quote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def parse_ris_file(ris_path: str) -> List[Dict]:
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
            elif line.startswith("T2  -"):
                current["journal"] = line[5:].strip()
        if current.get("doi"):
            papers.append(current)
    for paper in papers:
        if paper.get("authors"):
            paper["first_author"] = paper["authors"][0].split(",")[0]
        else:
            paper["first_author"] = "Unknown"
    return papers


def sanitize_filename(name: str, max_len: int = 180) -> str:
    name = re.sub(r'[/\\:*?"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > max_len:
        name = name[:max_len]
    return name


def get_publisher_info(doi: str) -> Dict:
    doi_lower = doi.lower()
    if (
        "/adma." in doi_lower
        or "/anie." in doi_lower
        or "/smtd." in doi_lower
        or "/cssc." in doi_lower
        or "wiley" in doi_lower
    ):
        return {
            "name": "wiley",
            "pdf_url": f"https://advanced.onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
            "manual_url": f"https://doi.org/{doi}",
        }
    elif "/apenergy" in doi_lower or "/ijhydene" in doi_lower or "10.1016" in doi_lower:
        return {
            "name": "elsevier",
            "pdf_url": f"https://www.sciencedirect.com/science/article/pii/{doi.split('/')[-1]}/pdfft",
            "manual_url": f"https://doi.org/{doi}",
        }
    elif "10.3390" in doi_lower:
        suffix = doi.replace("10.3390/", "")
        return {
            "name": "mdpi",
            "pdf_url": f"https://www.mdpi.com/{suffix}/pdf",
            "manual_url": f"https://www.mdpi.com/{suffix}",
        }
    elif "acsami" in doi_lower or "10.1021" in doi_lower:
        return {
            "name": "acs",
            "pdf_url": f"https://pubs.acs.org/doi/pdf/{doi}",
            "manual_url": f"https://doi.org/{doi}",
        }
    elif "springer" in doi_lower or "nature" in doi_lower:
        return {
            "name": "springer",
            "pdf_url": f"https://link.springer.com/content/pdf/{doi}.pdf",
            "manual_url": f"https://doi.org/{doi}",
        }
    else:
        return {
            "name": "unknown",
            "pdf_url": None,
            "manual_url": f"https://doi.org/{doi}",
        }


def run_public_download(
    papers: List[Dict], output_dir: str, success_dois: Set[str]
) -> Set[str]:
    logger.info("\n" + "=" * 60)
    logger.info("第一阶段: 公开渠道下载 (Unpaywall + CORE)")
    logger.info("=" * 60)

    import requests
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    )

    new_success = set()

    def download_from_core(paper: Dict) -> bool:
        doi = paper["doi"]
        if doi in success_dois or doi in new_success:
            return True
        title = paper.get("title", "Unknown")[:50]

        try:
            search_url = f"https://core.ac.uk/search?q={quote(doi)}"
            logger.info(f"[CORE] {doi}: 搜索中...")
            resp = session.get(search_url, timeout=20, verify=False)

            if resp.status_code != 200:
                logger.debug(f"[CORE] 搜索失败: HTTP {resp.status_code}")
                return False

            pdf_pattern = re.compile(
                r'href=["\']([^"\']*core\.ac\.uk/download[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(resp.text)

            for pdf_url in pdf_links[:3]:
                logger.info(f"[CORE] 找到 PDF: {pdf_url[:60]}...")
                try:
                    pdf_resp = session.get(pdf_url, timeout=60, verify=False)
                    if pdf_resp.status_code == 200 and len(pdf_resp.content) > 1000:
                        if pdf_resp.content[:4] == b"%PDF":
                            filename = f"{paper.get('first_author', 'Unknown')}_{paper.get('year', '')}_{title}_{doi.replace('/', '_')}.pdf"
                            filename = sanitize_filename(filename)
                            filepath = os.path.join(output_dir, filename)
                            with open(filepath, "wb") as f:
                                f.write(pdf_resp.content)
                            logger.info(
                                f"✅ [CORE] 下载成功: {len(pdf_resp.content):,} bytes"
                            )
                            return True
                except Exception as e:
                    logger.debug(f"[CORE] PDF 下载失败: {e}")

            logger.debug(f"[CORE] 未找到有效 PDF")
            return False

        except Exception as e:
            logger.debug(f"[CORE] {doi} 失败: {e}")
            return False

    def download_from_unpaywall(paper: Dict) -> bool:
        doi = paper["doi"]
        if doi in success_dois or doi in new_success:
            return True
        title = paper.get("title", "Unknown")[:50]

        try:
            url = f"https://api.unpaywall.org/v2/{doi}?email=test@example.com"
            resp = session.get(url, timeout=15)

            if resp.status_code != 200:
                return False

            data = resp.json()
            if data.get("is_oa") and data.get("best_oa_location"):
                pdf_url = data["best_oa_location"].get("url_for_pdf") or data[
                    "best_oa_location"
                ].get("url")
                if pdf_url:
                    logger.info(f"[Unpaywall] {doi}: {pdf_url[:60]}...")
                    try:
                        pdf_resp = session.get(pdf_url, timeout=30, verify=False)
                        if (
                            pdf_resp.status_code == 200
                            and pdf_resp.content[:4] == b"%PDF"
                        ):
                            filename = f"{paper.get('first_author', 'Unknown')}_{paper.get('year', '')}_{title}_{doi.replace('/', '_')}.pdf"
                            filename = sanitize_filename(filename)
                            filepath = os.path.join(output_dir, filename)
                            with open(filepath, "wb") as f:
                                f.write(pdf_resp.content)
                            logger.info(
                                f"✅ [Unpaywall] 下载成功: {len(pdf_resp.content):,} bytes"
                            )
                            return True
                    except Exception as e:
                        logger.debug(f"[Unpaywall] PDF 下载失败: {e}")
        except Exception as e:
            logger.debug(f"[Unpaywall] {doi} 失败: {e}")
        return False

    for paper in papers:
        doi = paper["doi"]
        if doi in success_dois or doi in new_success:
            continue

        logger.info(f"\n[{doi}] 尝试公开渠道...")

        if download_from_unpaywall(paper):
            new_success.add(doi)
            continue

        if download_from_core(paper):
            new_success.add(doi)
            continue

        logger.warning(f"[{doi}] 公开渠道下载失败")

    return new_success


class BrowserDownloader:
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        self.playwright = None
        self.browser = None
        self.context = None
        os.makedirs(download_dir, exist_ok=True)

    async def connect_cdp(self, cdp_url: str = "http://127.0.0.1:9222") -> bool:
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright 未安装")
            return False
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(cdp_url)
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                logger.info(f"✅ 已连接到 CDP 浏览器")
                return True
            return False
        except Exception as e:
            logger.error(f"CDP 连接失败: {e}")
            return False

    async def close(self):
        self.context = None
        self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def download_from_url(
        self, url: str, doi: str, publisher: str, metadata: Optional[Dict] = None
    ) -> Optional[str]:
        if not self.context:
            return None

        pdf_data_holder = {"data": None}

        pages = self.context.pages
        page = pages[-1] if pages else await self.context.new_page()

        async def capture_pdf(route, request):
            try:
                response = await route.fetch(timeout=15000)
                body = await response.body()
                content_type = response.headers.get("content-type", "")
                if "pdf" in content_type.lower() or (
                    len(body) > 4 and body[:4] == b"%PDF"
                ):
                    logger.info(f"[浏览器] 拦截到 PDF: {len(body):,} bytes")
                    pdf_data_holder["data"] = body
                await route.fulfill(response=response)
            except Exception as e:
                try:
                    await route.continue_()
                except:
                    pass

        try:
            await page.route("**/*", capture_pdf)
            logger.info(f"访问: {url}")

            try:
                response = await page.goto(
                    url, timeout=60000, wait_until="domcontentloaded"
                )
            except Exception as e:
                logger.warning(f"页面加载超时: {e}")
                response = None

            if not response:
                try:
                    await page.unroute("**/*", capture_pdf)
                except:
                    pass
                return None

            await asyncio.sleep(3)

            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except:
                pass

            pdf_data = pdf_data_holder["data"]

            if not pdf_data:
                for _ in range(8):
                    await asyncio.sleep(1)
                    if pdf_data_holder["data"]:
                        pdf_data = pdf_data_holder["data"]
                        break

            if not pdf_data and publisher == "elsevier":
                logger.info("[Elsevier] 尝试点击下载按钮...")
                try:
                    download_btn = await page.query_selector(
                        "a.download-link, button.download-pdf, a[href*='pdfft'], #download-link"
                    )
                    if download_btn:
                        await download_btn.click()
                        await asyncio.sleep(5)
                        pdf_data = pdf_data_holder["data"]
                except:
                    pass

            if not pdf_data and publisher == "mdpi":
                logger.info("[MDPI] 尝试查找 PDF 链接...")
                try:
                    pdf_link = await page.query_selector(
                        "a[href$='.pdf'], a.download-pdf"
                    )
                    if pdf_link:
                        href = await pdf_link.get_attribute("href")
                        if href:
                            if href.startswith("/"):
                                href = "https://www.mdpi.com" + href
                            logger.info(f"[MDPI] 找到 PDF 链接: {href[:60]}")
                            await page.goto(href, timeout=30000)
                            await asyncio.sleep(3)
                            pdf_data = pdf_data_holder["data"]
                except:
                    pass

            try:
                await page.unroute("**/*", capture_pdf)
            except:
                pass

            if not pdf_data or pdf_data[:4] != b"%PDF":
                return None

            if metadata:
                author = metadata.get("first_author", "Unknown")
                year = metadata.get("year", "")
                title = metadata.get("title", "Untitled")[:50]
                doi_safe = doi.replace("/", "_")
                filename = f"{author}_{year}_{title}_{doi_safe}.pdf"
                filename = sanitize_filename(filename)
            else:
                filename = f"browser_{doi.replace('/', '_')}.pdf"

            filepath = os.path.join(self.download_dir, filename)
            with open(filepath, "wb") as f:
                f.write(pdf_data)
            return filepath

        except Exception as e:
            logger.error(f"下载失败: {e}")
            try:
                await page.unroute("**/*", capture_pdf)
            except:
                pass
            return None


async def run_browser_download(
    papers: List[Dict], failed_dois: Set[str], output_dir: str, cdp_url: str
) -> Set[str]:
    logger.info("\n" + "=" * 60)
    logger.info("第二阶段: 浏览器官方渠道下载")
    logger.info("=" * 60)

    new_success = set()
    failed_papers = [p for p in papers if p["doi"] in failed_dois]

    if not failed_papers:
        return new_success

    browser = BrowserDownloader(output_dir)

    if not await browser.connect_cdp(cdp_url):
        logger.error("无法连接浏览器，跳过此阶段")
        return new_success

    try:
        for paper in failed_papers:
            doi = paper["doi"]
            publisher_info = get_publisher_info(doi)
            publisher = publisher_info["name"]
            pdf_url = publisher_info["pdf_url"]

            if publisher == "unknown" or not pdf_url:
                logger.info(f"[{doi}] 未知出版商，跳过")
                continue

            logger.info(f"\n[{doi}] 出版商: {publisher}")
            filepath = await browser.download_from_url(pdf_url, doi, publisher, paper)

            if filepath:
                new_success.add(doi)
                logger.info(f"✅ 下载成功: {filepath}")
            else:
                logger.warning(f"❌ 下载失败")

            await asyncio.sleep(1)
    finally:
        await browser.close()

    return new_success


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="完整论文下载流程")
    parser.add_argument("ris_file", help="RIS 文件路径")
    parser.add_argument("--output", "-o", default="./downloads", help="输出目录")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222", help="CDP 地址")
    parser.add_argument("--skip-public", action="store_true", help="跳过公开渠道")
    parser.add_argument("--skip-browser", action="store_true", help="跳过浏览器官方")

    args = parser.parse_args()

    if not os.path.exists(args.ris_file):
        logger.error(f"文件不存在: {args.ris_file}")
        sys.exit(1)

    papers = parse_ris_file(args.ris_file)
    logger.info(f"📋 解析到 {len(papers)} 篇论文")

    os.makedirs(args.output, exist_ok=True)

    all_success: Set[str] = set()

    if not args.skip_public:
        public_success = run_public_download(papers, args.output, all_success)
        all_success.update(public_success)
        logger.info(
            f"\n📊 公开渠道完成: {len(public_success)} 篇新下载，累计 {len(all_success)} 篇"
        )

    if not args.skip_browser:
        failed_dois = set(p["doi"] for p in papers) - all_success
        if failed_dois:
            browser_success = await run_browser_download(
                papers, failed_dois, args.output, args.cdp_url
            )
            all_success.update(browser_success)
            logger.info(
                f"\n📊 浏览器官方完成: {len(browser_success)} 篇新下载，累计 {len(all_success)} 篇"
            )

    failed_dois = set(p["doi"] for p in papers) - all_success

    print("\n" + "=" * 60)
    print("📊 最终下载报告")
    print("=" * 60)
    print(f"总论文数: {len(papers)}")
    print(f"成功下载: {len(all_success)}")
    print(f"下载失败: {len(failed_dois)}")
    print(f"成功率: {len(all_success) / len(papers) * 100:.1f}%")

    if failed_dois:
        print("\n❌ 以下论文下载失败，请手动下载:")
        for doi in failed_dois:
            paper = next((p for p in papers if p["doi"] == doi), None)
            if paper:
                title = paper.get("title", "N/A")
                if len(title) > 60:
                    title = title[:60] + "..."
                publisher_info = get_publisher_info(doi)
                manual_url = publisher_info.get("manual_url", f"https://doi.org/{doi}")
                print(f"\n  📄 DOI: {doi}")
                print(f"     标题: {title}")
                print(f"     手动下载: {manual_url}")

    print(f"\n✅ 下载成功的文件保存在: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
