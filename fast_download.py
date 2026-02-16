#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速并行下载器 - 高并发版本
"""

import os
import re
import sys
import logging
from typing import Dict, List, Set
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


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


class FastDownloader:
    def __init__(self, output_dir: str, workers: int = 15):
        self.output_dir = output_dir
        self.workers = workers
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        os.makedirs(output_dir, exist_ok=True)

        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        self.session = requests.Session()
        retry = Retry(
            total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(
            max_retries=retry, pool_connections=workers, pool_maxsize=workers
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "*/*",
            }
        )

    def try_unpaywall(self, doi: str) -> bytes:
        try:
            url = f"https://api.unpaywall.org/v2/{doi}?email=test@example.com"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("is_oa") and data.get("best_oa_location"):
                    pdf_url = data["best_oa_location"].get("url_for_pdf")
                    if pdf_url:
                        pdf_resp = self.session.get(pdf_url, timeout=30, verify=False)
                        if (
                            pdf_resp.status_code == 200
                            and pdf_resp.content[:4] == b"%PDF"
                        ):
                            return pdf_resp.content
        except:
            pass
        return None

    def try_core(self, doi: str) -> bytes:
        try:
            search_url = f"https://core.ac.uk/search?q={quote(doi)}"
            resp = self.session.get(search_url, timeout=15, verify=False)
            if resp.status_code != 200:
                return None

            pdf_pattern = re.compile(
                r'href=["\']([^"\']*core\.ac\.uk/download[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(resp.text)

            for pdf_url in pdf_links[:2]:
                try:
                    pdf_resp = self.session.get(pdf_url, timeout=30, verify=False)
                    if pdf_resp.status_code == 200 and len(pdf_resp.content) > 1000:
                        if pdf_resp.content[:4] == b"%PDF":
                            return pdf_resp.content
                except:
                    pass
        except:
            pass
        return None

    def download_paper(self, paper: Dict, idx: int, total: int) -> str:
        doi = paper["doi"]
        title = paper.get("title", "Unknown")[:40]

        pdf_data = self.try_unpaywall(doi)
        source = "unpaywall"

        if not pdf_data:
            pdf_data = self.try_core(doi)
            source = "core"

        if pdf_data:
            author = paper.get("first_author", "Unknown")
            year = paper.get("year", "")
            filename = f"{author}_{year}_{title}_{doi.replace('/', '_')}.pdf"
            filename = sanitize_filename(filename)
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, "wb") as f:
                f.write(pdf_data)

            with self.lock:
                self.success_count += 1
                logger.info(
                    f"[{idx + 1}/{total}] ✅ {source}: {doi[:50]} ({self.success_count}/{self.success_count + self.fail_count})"
                )
            return doi

        with self.lock:
            self.fail_count += 1
        return None

    def run(self, papers: List[Dict]) -> Set[str]:
        total = len(papers)
        success_dois = set()

        logger.info(f"开始并行下载 {total} 篇论文 (并发数: {self.workers})")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self.download_paper, p, i, total): p
                for i, p in enumerate(papers)
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        success_dois.add(result)
                except Exception as e:
                    pass

        elapsed = time.time() - start_time
        logger.info(f"\n完成! 耗时: {elapsed / 60:.1f} 分钟")
        logger.info(f"成功: {self.success_count}, 失败: {self.fail_count}")

        return success_dois


def generate_html(papers: List[Dict], success_dois: Set[str], output_dir: str):
    failed = [p for p in papers if p["doi"] not in success_dois]
    if not failed:
        return None

    html = (
        """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>手动下载</title>
<style>
body{font-family:system-ui;padding:20px;background:#f5f5f5}
.card{background:#fff;padding:15px;margin:10px 0;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}
.doi{font-family:monospace;color:#666;font-size:12px}
.title{font-weight:600;margin:8px 0}
.btn{display:inline-block;padding:6px 12px;margin:4px;border-radius:4px;text-decoration:none;font-size:13px}
.btn-primary{background:#0066cc;color:#fff}
.btn-secondary{background:#6c757d;color:#fff}
</style></head><body>
<h1>需手动下载: """
        + str(len(failed))
        + """ 篇</h1>
"""
    )

    for p in failed:
        doi = p["doi"]
        title = p.get("title", "N/A")[:80]
        html += f"""<div class="card">
<div class="doi">{doi}</div>
<div class="title">{title}</div>
<a href="https://doi.org/{doi}" target="_blank" class="btn btn-primary">官方下载</a>
<a href="https://sci-hub.se/{doi}" target="_blank" class="btn btn-secondary">Sci-Hub</a>
</div>"""

    html += "</body></html>"

    path = os.path.join(output_dir, "manual_download.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("ris_file")
    parser.add_argument("-o", "--output", default="./downloads")
    parser.add_argument("-w", "--workers", type=int, default=15)
    args = parser.parse_args()

    papers = parse_ris_file(args.ris_file)
    logger.info(f"解析到 {len(papers)} 篇论文")

    downloader = FastDownloader(args.output, workers=args.workers)
    success_dois = downloader.run(papers)

    html_path = generate_html(papers, success_dois, args.output)
    if html_path:
        logger.info(f"手动下载页面: {html_path}")
        import webbrowser

        webbrowser.open(f"file://{os.path.abspath(html_path)}")


if __name__ == "__main__":
    import urllib3

    urllib3.disable_warnings()
    main()
