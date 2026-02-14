"""核心下载器模块"""

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..sources import BaseSource, create_source
from ..utils.config import Config
from ..utils.logger import get_logger, setup_logger
from ..utils.report import HTMLReportGenerator
from ..utils.validator import validate_pdf


class MultiSourceDownloader:
    """多来源下载器 (模块化版本 v4.0)"""

    def __init__(
        self,
        config: Optional[Config] = None,
        config_path: Optional[str] = None,
        max_workers: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.config = config or Config(config_path)

        self.max_workers = (
            max_workers if max_workers is not None else self.config.get_max_workers()
        )
        self.max_retries = (
            max_retries if max_retries is not None else self.config.get_max_retries()
        )

        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

        self.output_dir = self.config.get_output_dir()
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.results: Dict[str, List[Any]] = {"success": [], "failed": []}
        self.lock = Lock()
        self.doi_metadata: Dict[str, Dict[str, str]] = {}

        self.logger = setup_logger(
            "paper_downloader",
            level=self.config.get("logging.level", "INFO"),
            log_file=self.config.get("logging.file"),
            console=self.config.get("logging.console", True),
        )

        self.html_report = HTMLReportGenerator(
            self.output_dir, self.max_workers, self.max_retries
        )

        self._init_sources()

    def _init_sources(self) -> None:
        """初始化下载源"""
        self.sources: List[Tuple[str, BaseSource, bool]] = []

        source_needs_no_proxy = {
            "Sci-Hub": True,
            "Google Scholar": True,
            "ResearchGate": True,
        }

        for source_name in self.config.get_enabled_sources():
            source_config = self.config.get_source_config(source_name)
            source = create_source(source_name, self.session, source_config)
            needs_no_proxy = source_needs_no_proxy.get(source_name, False)
            self.sources.append((source_name, source, needs_no_proxy))

    def parse_ris_metadata(self, ris_file: str) -> Dict[str, Dict[str, str]]:
        """解析 RIS 文件元数据"""
        metadata = {}
        current_doi: Optional[str] = None
        current_entry: Dict[str, str] = {"year": "", "journal": "", "first_author": ""}

        with open(ris_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                if " - " in line:
                    field, value = line.split(" - ", 1)
                    field = field.strip()
                    value = value.strip()

                    if field == "DO":
                        if current_doi:
                            metadata[current_doi] = current_entry.copy()
                        current_doi = value
                        current_entry = {
                            "year": current_entry["year"],
                            "journal": current_entry["journal"],
                            "first_author": current_entry["first_author"],
                        }

                    elif field == "PY":
                        current_entry["year"] = value[:4] if len(value) > 4 else value

                    elif field in ["T2", "J9", "JI"]:
                        if not current_entry["journal"]:
                            current_entry["journal"] = re.sub(
                                r'[\\/*?:"<>|]', "", value
                            )

                    elif field == "AU":
                        if not current_entry["first_author"]:
                            if ", " in value:
                                value = value.split(", ")[0]
                            current_entry["first_author"] = value

                elif line.startswith("ER"):
                    if current_doi:
                        metadata[current_doi] = current_entry.copy()
                    current_doi = None
                    current_entry = {"year": "", "journal": "", "first_author": ""}

        if current_doi:
            metadata[current_doi] = current_entry.copy()

        return metadata

    def generate_filename(self, doi: str, source: str) -> str:
        """生成文件名"""
        metadata = self.doi_metadata.get(doi, {})
        year = metadata.get("year", "Unknown")
        journal = metadata.get("journal", "Unknown")
        author = metadata.get("first_author", "Unknown")

        safe_year = re.sub(r'[\\/*?:"<>|]', "", str(year))
        safe_journal = re.sub(r'[\\/*?:"<>|]', "", journal)
        safe_author = re.sub(r'[\\/*?:"<>|]', "", author)
        safe_source = re.sub(r'[\\/*?:"<>|]', "", source)

        return f"{safe_year}-{safe_journal}-{safe_author}-{safe_source}"

    def download_doi(self, doi: str, index: int = 1, total: int = 1) -> bool:
        """下载单个 DOI"""
        attempts: List[Dict[str, Any]] = []

        with self.lock:
            self.html_report.add_item(
                index=index,
                doi=doi,
                status="processing",
                attempts=attempts,
            )

        retry_count = 0
        while retry_count <= self.max_retries:
            for source_name, source, needs_no_proxy in self.sources:
                use_proxy = not needs_no_proxy
                proxies = self.config.get_proxy_config(use_china_network=use_proxy)

                attempt = {
                    "source": source_name,
                    "retry": retry_count + 1,
                    "status": "trying",
                }
                attempts.append(attempt)

                self.logger.info(
                    f"[{index}/{total}] [{source_name}] 尝试 #{retry_count + 1}"
                )

                try:
                    result = source.download(doi, proxies)

                    if result.get("success"):
                        if "direct_response" in result:
                            save_result = self._save_direct_response(
                                result, doi, source_name
                            )
                        else:
                            save_result = self._download_and_save(
                                result.get("pdf_url", ""), doi, source_name, proxies
                            )

                        if save_result.get("success"):
                            attempt["status"] = "success"

                            with self.lock:
                                for item in self.html_report.report_data["items"]:
                                    if item["doi"] == doi:
                                        item["status"] = "success"
                                        item["final_source"] = source_name
                                        item["file"] = save_result.get("file")
                                        item["size"] = save_result.get("size", 0)
                                        break

                            with self.lock:
                                self.results["success"].append(
                                    {
                                        "doi": doi,
                                        "source": source_name,
                                        "file": save_result.get("file"),
                                        "retry": retry_count,
                                    }
                                )

                            self.logger.info(
                                f"[{index}/{total}] {source_name} 下载成功"
                            )
                            return True

                    attempt["status"] = "failed"
                    self.logger.debug(f"[{index}/{total}] {source_name} 失败")

                except Exception as e:
                    attempt["status"] = "error"
                    attempt["error"] = str(e)
                    self.logger.error(f"[{index}/{total}] {source_name} 错误: {e}")

                time.sleep(0.5)

            retry_count += 1
            if retry_count <= self.max_retries:
                self.logger.info(f"重试 #{retry_count + 1}/{self.max_retries + 1}")
                time.sleep(2)

        with self.lock:
            for item in self.html_report.report_data["items"]:
                if item["doi"] == doi:
                    item["status"] = "failed"
                    break
            self.results["failed"].append(doi)

        self.logger.warning(f"[{index}/{total}] {doi} 所有来源均失败")
        return False

    def _download_and_save(
        self,
        url: str,
        doi: str,
        source: str,
        proxies: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """下载并保存 PDF"""
        if not url:
            return {"success": False, "error": "URL 为空"}

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Referer": f"https://doi.org/{doi}",
            }

            response = self.session.get(
                url,
                timeout=60,
                stream=True,
                proxies=proxies,
                headers=headers,
                allow_redirects=True,
            )

            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}

            content_type = response.headers.get("Content-Type", "").lower()
            if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                return {"success": False, "error": f"非 PDF 响应: {content_type}"}

            filename = self.generate_filename(doi, source) + ".pdf"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            if self.config.get("download.validate_pdf", True):
                valid, msg = validate_pdf(filepath)
                if not valid:
                    os.remove(filepath)
                    return {"success": False, "error": f"PDF 无效: {msg}"}

            file_size = os.path.getsize(filepath)
            self.logger.info(f"保存: {filename} ({file_size:,} bytes)")

            return {"success": True, "file": filepath, "size": file_size}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _save_direct_response(
        self, result: Dict[str, Any], doi: str, source: str
    ) -> Dict[str, Any]:
        """保存直接响应（如 Sci-Hub 直接返回 PDF）"""
        filename = self.generate_filename(doi, source) + ".pdf"
        filepath = os.path.join(self.output_dir, filename)

        response = self.session.get(
            result.get("pdf_url", ""),
            timeout=self.config.get_download_timeout(),
            stream=True,
        )

        if response.status_code != 200:
            return {"success": False, "error": f"HTTP {response.status_code}"}

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(filepath)
        return {"success": True, "file": filepath, "size": file_size}

    def batch_download_from_ris(self, ris_file: str) -> None:
        """从 RIS 文件批量下载"""
        self.logger.info("=" * 70)
        self.logger.info("📚 RIS 文件多渠道批量下载器 v4.0 (模块化版本)")
        self.logger.info("=" * 70)
        self.logger.info(f"📄 RIS 文件: {ris_file}")

        self.logger.info("📖 解析 RIS 元数据...")
        self.doi_metadata = self.parse_ris_metadata(ris_file)
        dois = list(self.doi_metadata.keys())

        self.logger.info(f"📋 找到 {len(dois)} 个 DOI")
        self.logger.info(f"🚀 开始并发下载 (最大并发数: {self.max_workers})")
        self.logger.info(f"🔧 最大重试次数: {self.max_retries}")
        self.logger.info(f"📁 保存目录: {self.output_dir}")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.download_doi, doi, i + 1, len(dois)): (i, doi)
                for i, doi in enumerate(dois)
            }

            for future in as_completed(futures):
                idx, doi = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"[{idx + 1}] {doi} 异常: {e}")
                    with self.lock:
                        self.results["failed"].append(doi)

        self.html_report.update_summary(
            total=len(dois),
            success=len(self.results["success"]),
            failed=len(self.results["failed"]),
        )

        self._print_summary(dois)
        self._generate_reports(dois)

    def _print_summary(self, dois: List[str]) -> None:
        """打印下载总结"""
        self.logger.info("=" * 70)
        self.logger.info("📊 下载总结")
        self.logger.info("=" * 70)

        self.logger.info(f"✅ 成功: {len(self.results['success'])} 篇")
        for item in self.results["success"]:
            self.logger.info(f"   ✓ {item['doi']} - {item['source']}")

        self.logger.info(f"❌ 失败: {len(self.results['failed'])} 篇")
        for doi in self.results["failed"]:
            self.logger.info(f"   ✗ {doi}")

        success_rate = len(self.results["success"]) / len(dois) * 100 if dois else 0
        self.logger.info(f"📈 成功率: {success_rate:.1f}%")

    def _generate_reports(self, dois: List[str]) -> None:
        """生成报告"""
        success_rate = len(self.results["success"]) / len(dois) * 100 if dois else 0

        log_file = os.path.join(self.output_dir, "download_summary.txt")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("RIS 文件批量下载总结 (v4.0 模块化版本)\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总计: {len(dois)} 篇\n")
            f.write(f"成功: {len(self.results['success'])} 篇\n")
            f.write(f"失败: {len(self.results['failed'])} 篇\n")
            f.write(f"成功率: {success_rate:.1f}%\n\n")

            f.write("成功列表:\n")
            for item in self.results["success"]:
                f.write(f"  {item['doi']}\n")
                f.write(f"    来源: {item['source']}\n\n")

            f.write("失败列表:\n")
            for doi in self.results["failed"]:
                f.write(f"  {doi}\n")

        self.logger.info(f"📝 详细日志: {log_file}")

        if self.config.get("report.generate_html", True):
            html_file = self.html_report.generate()
            self.logger.info(f"🌐 HTML 报告: {html_file}")
