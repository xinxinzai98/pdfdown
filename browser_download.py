#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充下载 - 浏览器 CDP 模式
"""

import os
import re
import sys
import asyncio
import logging
from typing import Dict, List, Set, Optional
from urllib.parse import quote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

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
        or "/aenm." in doi_lower
        or "wiley" in doi_lower
        or "10.1002" in doi_lower
    ):
        return {
            "name": "wiley",
            "pdf_url": f"https://advanced.onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
        }
    elif "10.1016" in doi_lower:
        return {
            "name": "elsevier",
            "pdf_url": f"https://www.sciencedirect.com/science/article/pii/{doi.split('/')[-1]}/pdfft",
        }
    elif "10.1039" in doi_lower:
        return {
            "name": "rsc",
            "pdf_url": f"https://pubs.rsc.org/en/content/articlepdf/{doi}",
        }
    elif "10.1021" in doi_lower:
        return {"name": "acs", "pdf_url": f"https://pubs.acs.org/doi/pdf/{doi}"}
    elif "10.1007" in doi_lower or "springer" in doi_lower:
        return {
            "name": "springer",
            "pdf_url": f"https://link.springer.com/content/pdf/{doi}.pdf",
        }
    elif "10.3390" in doi_lower:
        suffix = doi.replace("10.3390/", "")
        return {"name": "mdpi", "pdf_url": f"https://www.mdpi.com/{suffix}/pdf"}
    else:
        return {"name": "unknown", "pdf_url": None}


class BrowserDownloader:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.playwright = None
        self.browser = None
        self.context = None
        self.success_count = 0
        self.fail_count = 0

    async def connect(self, cdp_url: str = "http://127.0.0.1:9222") -> bool:
        if not PLAYWRIGHT_AVAILABLE:
            return False
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(cdp_url)
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                logger.info("已连接浏览器 CDP")
                return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
        return False

    async def close(self):
        self.context = None
        self.browser = None
        if self.playwright:
            await self.playwright.stop()

    async def download(self, paper: Dict) -> bool:
        doi = paper["doi"]
        info = get_publisher_info(doi)

        if info["name"] == "unknown" or not info["pdf_url"]:
            return False

        url = info["pdf_url"]
        publisher = info["name"]

        pdf_data_holder = {"data": None}
        pages = self.context.pages
        page = pages[-1] if pages else await self.context.new_page()

        async def capture(route, request):
            try:
                response = await route.fetch(timeout=15000)
                body = await response.body()
                ct = response.headers.get("content-type", "")
                if "pdf" in ct.lower() or (len(body) > 4 and body[:4] == b"%PDF"):
                    pdf_data_holder["data"] = body
                await route.fulfill(response=response)
            except:
                try:
                    await route.continue_()
                except:
                    pass

        try:
            await page.route("**/*", capture)
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except:
                pass

            pdf_data = pdf_data_holder["data"]

            if not pdf_data:
                for _ in range(5):
                    await asyncio.sleep(1)
                    if pdf_data_holder["data"]:
                        pdf_data = pdf_data_holder["data"]
                        break

            try:
                await page.unroute("**/*", capture)
            except:
                pass

            if not pdf_data or pdf_data[:4] != b"%PDF":
                self.fail_count += 1
                return False

            author = paper.get("first_author", "Unknown")
            year = paper.get("year", "")
            title = paper.get("title", "Untitled")[:50]
            filename = f"{author}_{year}_{title}_{doi.replace('/', '_')}.pdf"
            filename = sanitize_filename(filename)

            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(pdf_data)

            self.success_count += 1
            logger.info(f"✅ [{publisher}] {doi[:50]}...")
            return True

        except Exception as e:
            self.fail_count += 1
            try:
                await page.unroute("**/*", capture)
            except:
                pass
            return False


def get_downloaded_dois(output_dir: str) -> Set[str]:
    dois = set()
    for f in os.listdir(output_dir):
        if f.endswith(".pdf"):
            parts = f.split("_")
            if len(parts) >= 4:
                doi_part = parts[-1].replace(".pdf", "")
                dois.add(doi_part)
    return dois


async def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("ris_file")
    parser.add_argument("-o", "--output", default="./downloads")
    args = parser.parse_args()

    papers = parse_ris_file(args.ris_file)
    downloaded = get_downloaded_dois(args.output)

    failed_papers = [
        p
        for p in papers
        if p["doi"].replace("/", "_") not in downloaded
        and p["doi"].replace("/", "_").replace(".", "_") not in downloaded
    ]

    # 更精确匹配
    failed_papers = []
    for p in papers:
        doi = p["doi"]
        doi_safe = doi.replace("/", "_")
        found = False
        for d in downloaded:
            if doi_safe in d or d in doi_safe:
                found = True
                break
        if not found:
            failed_papers.append(p)

    logger.info(
        f"总论文: {len(papers)}, 已下载: {len(downloaded)}, 待下载: {len(failed_papers)}"
    )

    if not failed_papers:
        logger.info("全部下载完成!")
        return

    # 按出版商分组
    by_publisher = {}
    for p in failed_papers:
        info = get_publisher_info(p["doi"])
        pub = info["name"]
        if pub not in by_publisher:
            by_publisher[pub] = []
        by_publisher[pub].append(p)

    logger.info("待下载分布:")
    for pub, papers_list in sorted(by_publisher.items(), key=lambda x: -len(x[1])):
        logger.info(f"  {pub}: {len(papers_list)} 篇")

    downloader = BrowserDownloader(args.output)
    if not await downloader.connect():
        logger.error("无法连接浏览器")
        return

    try:
        # 只下载支持的出版商
        supported = ["wiley", "elsevier", "acs", "springer", "rsc"]

        for pub in supported:
            if pub not in by_publisher:
                continue

            papers_list = by_publisher[pub]
            logger.info(f"\n开始下载 {pub}: {len(papers_list)} 篇")

            for i, p in enumerate(papers_list):
                doi = p["doi"]
                logger.info(f"[{i + 1}/{len(papers_list)}] {doi}")
                await downloader.download(p)
                await asyncio.sleep(0.5)

            logger.info(f"{pub} 完成: 成功 {downloader.success_count}")

    finally:
        await downloader.close()

    logger.info(
        f"\n总计: 成功 {downloader.success_count}, 失败 {downloader.fail_count}"
    )


if __name__ == "__main__":
    asyncio.run(main())
