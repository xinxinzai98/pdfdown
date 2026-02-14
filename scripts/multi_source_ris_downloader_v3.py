#!/usr/bin/env python3
"""
RIS 文件多渠道批量下载器 (增强版 v3.0)

改进功能:
- 并发下载优化
- 代理支持（海外代理 + 中国大学内网）
- 更多下载源（10+）
- 增强重试机制
- 网页可视化报告
"""

import re
import os
import sys
import time
import json
import requests
from urllib.parse import quote, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from datetime import datetime


class MultiSourceDownloader:
    """多来源下载器 (增强版)"""

    def __init__(self, max_workers=3, max_retries=2):
        self.max_workers = max_workers
        self.max_retries = max_retries

        self.session = requests.Session()
        self.session.trust_env = False  # 禁用系统代理
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }
        )

        self.output_dir = "ris_downloads"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.results = {"success": [], "failed": [], "in_progress": []}
        self.lock = Lock()

        # 存储 DOI 元数据：年份、刊物、第一作者
        self.doi_metadata = {}

        self.html_report = {
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": None,
            "total": 0,
            "success": 0,
            "failed": 0,
            "items": [],
        }

    def get_proxy_config(self, use_china_network=False):
        """获取代理配置

        Args:
            use_china_network: 是否使用中国大学内网（绕过代理）

        Returns:
            proxies 字典或 None
        """
        if use_china_network:
            return None
        else:
            return {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

    def parse_ris_metadata(self, ris_file):
        """解析 RIS 文件，提取 DOI 的元数据

        Returns:
            dict: {doi: {"year": str, "journal": str, "first_author": str}}
        """
        metadata = {}
        current_doi = None
        current_entry = {"year": "", "journal": "", "first_author": ""}

        with open(ris_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 检查是否是字段开始
                if " - " in line:
                    field, value = line.split(" - ", 1)
                    field = field.strip()
                    value = value.strip()

                    # DOI
                    if field == "DO":
                        # 保存前一个条目
                        if current_doi:
                            metadata[current_doi] = current_entry.copy()
                        current_doi = value
                        current_entry = {"year": "", "journal": "", "first_author": ""}

                    # 年份 (PY)
                    elif field == "PY" and current_doi:
                        current_entry["year"] = value

                    # 刊物名称 (T2, J9, JI)
                    elif field in ["T2", "J9", "JI"] and current_doi:
                        if not current_entry["journal"]:
                            current_entry["journal"] = value

                    # 作者 (AU)
                    elif field == "AU" and current_doi:
                        if not current_entry["first_author"]:
                            current_entry["first_author"] = value

            # 保存最后一个条目
            if current_doi:
                metadata[current_doi] = current_entry.copy()

        # 清理数据
        for doi in metadata:
            # 提取年份（如果是完整的日期，只取年份）
            year = metadata[doi]["year"]
            if len(year) > 4:
                year = year[:4]
            metadata[doi]["year"] = year

            # 清理刊物名称（移除特殊字符）
            journal = metadata[doi]["journal"]
            journal = re.sub(r'[\\/*?:"<>|]', "", journal)
            journal = journal.strip()
            metadata[doi]["journal"] = journal

            # 清理作者名（格式化）
            author = metadata[doi]["first_author"]
            if author:
                # 格式: "Last, First" 或 "First Last"
                if ", " in author:
                    parts = author.split(", ")
                    if len(parts) >= 1:
                        author = parts[0]
                metadata[doi]["first_author"] = author

        return metadata

    def generate_filename(self, doi, source):
        """生成文件名：年份-刊物-第一作者-来源

        Args:
            doi: DOI
            source: 下载来源

        Returns:
            str: 文件名（不含扩展名）
        """
        # 获取元数据
        metadata = self.doi_metadata.get(doi, {})

        year = metadata.get("year", "Unknown")
        journal = metadata.get("journal", "Unknown")
        author = metadata.get("first_author", "Unknown")

        # 清理文件名（移除非法字符）
        safe_year = re.sub(r'[\\/*?:"<>|]', "", str(year))
        safe_journal = re.sub(r'[\\/*?:"<>|]', "", journal)
        safe_author = re.sub(r'[\\/*?:"<>|]', "", author)
        safe_source = re.sub(r'[\\/*?:"<>|]', "", source)

        # 生成文件名
        filename = f"{safe_year}-{safe_journal}-{safe_author}-{safe_source}"

        return filename

    def download_doi(self, doi, index=1, total=1):
        """尝试从多个来源下载单个 DOI（支持重试）

        Args:
            doi: DOI
            index: 当前索引
            total: 总数
        """
        sources = [
            ("Unpaywall API", self._try_unpaywall, False),
            ("Sci-Hub ⚠️", self._try_scihub, True),
            ("Semantic Scholar", self._try_semantic_scholar, False),
            ("arXiv", self._try_arxiv, False),
            ("CORE", self._try_core, False),
            ("Open Access Button", self._try_openaccess, False),
            ("Europe PMC", self._try_europe_pmc, False),
            ("PubMed", self._try_pubmed, False),
            ("Paperity", self._try_paperity, False),
            ("Google Scholar", self._try_google_scholar, True),
            ("ResearchGate", self._try_researchgate, True),
        ]

        with self.lock:
            self.html_report["items"].append(
                {
                    "index": index,
                    "doi": doi,
                    "status": "processing",
                    "attempts": [],
                    "final_source": None,
                    "file": None,
                    "size": 0,
                }
            )
            item = self.html_report["items"][-1]

        retry_count = 0

        while retry_count <= self.max_retries:
            for source_name, download_func, needs_proxy in sources:
                try:
                    use_proxy = not needs_proxy
                    proxies = self.get_proxy_config(use_china_network=use_proxy)

                    with self.lock:
                        item["attempts"].append(
                            {
                                "source": source_name,
                                "retry": retry_count + 1,
                                "status": "trying",
                            }
                        )

                    print(
                        f"[{index}/{total}] [{source_name}] 尝试 #{retry_count + 1} ...",
                        end=" ",
                    )

                    result = download_func(doi, proxies=proxies)

                    if result and result.get("success"):
                        print(f"✅ 成功")

                        with self.lock:
                            item["status"] = "success"
                            item["final_source"] = source_name
                            item["file"] = result.get("file")
                            item["size"] = result.get("size", 0)
                            item["attempts"][-1]["status"] = "success"

                            self.results["success"].append(
                                {
                                    "doi": doi,
                                    "source": source_name,
                                    "file": result.get("file"),
                                    "retry": retry_count,
                                }
                            )

                        return True
                    else:
                        print(f"❌ 失败")

                        with self.lock:
                            item["attempts"][-1]["status"] = "failed"

                    time.sleep(0.5)

                except Exception as e:
                    print(f"❌ 错误: {str(e)[:50]}")

                    with self.lock:
                        item["attempts"][-1]["status"] = "error"
                        item["attempts"][-1]["error"] = str(e)

            retry_count += 1
            if retry_count <= self.max_retries:
                print(f"    🔄 重试 #{retry_count + 1}/{self.max_retries + 1}...")
                time.sleep(2)

        with self.lock:
            item["status"] = "failed"
            self.results["failed"].append(doi)

        return False

    def _try_with_fallback(self, url, timeout=10, proxies=None, allow_redirects=True):
        """使用指定代理请求,失败时尝试无代理"""
        try:
            return self.session.get(
                url, timeout=timeout, proxies=proxies, allow_redirects=allow_redirects
            )
        except (
            requests.exceptions.ProxyError,
            requests.exceptions.Timeout,
            requests.exceptions.SSLError,
        ) as e:
            if proxies is not None:
                print(f"    🔁 代理失败,尝试无代理...")
                try:
                    return self.session.get(
                        url,
                        timeout=timeout,
                        proxies=None,
                        allow_redirects=allow_redirects,
                    )
                except Exception as e2:
                    raise e2
            raise

    def _try_unpaywall(self, doi, proxies=None):
        """尝试 Unpaywall API"""
        try:
            # Unpaywall API 请求需要无代理（使用 session.trust_env = False）
            url = f"https://api.unpaywall.org/v2/{doi}?email=894643096@qq.com"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("is_oa"):
                    pdf_url = data.get("best_oa_location", {}).get("url")
                    if pdf_url:
                        # 尝试多种方式下载 PDF
                        # 方法1: 使用配置的代理
                        result = self._download_and_save(
                            pdf_url, doi, "Unpaywall", proxies
                        )
                        if result.get("success"):
                            return result

                        # 方法2: 不使用代理
                        result = self._download_and_save(
                            pdf_url, doi, "Unpaywall", None
                        )
                        if result.get("success"):
                            return result

                        # 方法3: 使用海外代理
                        oversea_proxies = self.get_proxy_config(use_china_network=False)
                        result = self._download_and_save(
                            pdf_url, doi, "Unpaywall", oversea_proxies
                        )
                        if result.get("success"):
                            return result

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_semantic_scholar(self, doi, proxies=None):
        """尝试 Semantic Scholar"""
        try:
            url = f"https://api.semanticscholar.org/v1/paper/DOI:{doi}"
            response = self._try_with_fallback(url, timeout=10, proxies=proxies)

            if response.status_code == 200:
                data = response.json()

                oa_pdf = data.get("openAccessPdf")
                if oa_pdf:
                    pdf_url = oa_pdf.get("url")
                    if pdf_url:
                        return self._download_and_save(
                            pdf_url, doi, "Semantic_Scholar", proxies
                        )

                sources = data.get("sources", [])
                for source in sources:
                    url = source.get("url")
                    if url and "pdf" in url.lower():
                        return self._download_and_save(
                            url, doi, "Semantic_Scholar", proxies
                        )

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_arxiv(self, doi, proxies=None):
        """尝试 arXiv"""
        if "arxiv" not in doi.lower():
            return {"success": False}

        arxiv_pattern = re.compile(r"(?:10\.\d+/)?arxiv\.?/?(\d+\.\d+)", re.IGNORECASE)
        match = arxiv_pattern.search(doi)

        if match:
            arxiv_id = match.group(1)
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            return self._download_and_save(pdf_url, doi, "arXiv", proxies)

        return {"success": False}

    def _try_core(self, doi, proxies=None):
        """尝试 CORE"""
        try:
            url = f"https://core.ac.uk/search?q={quote(doi)}"
            response = self._try_with_fallback(url, timeout=10, proxies=proxies)

            pdf_pattern = re.compile(
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(response.text)

            if pdf_links:
                for pdf_url in pdf_links[:3]:
                    if pdf_url.startswith("https://core.ac.uk/download"):
                        return self._download_and_save(pdf_url, doi, "CORE", proxies)

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_openaccess(self, doi, proxies=None):
        """尝试开放获取按钮"""
        try:
            url = f"https://api.openaccessbutton.org/v2/{doi}?email=your@email.com"
            response = self._try_with_fallback(url, timeout=10, proxies=proxies)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("file_type") == "pdf":
                    pdf_url = data.get("file_url")
                    if pdf_url:
                        return self._download_and_save(
                            pdf_url, doi, "OpenAccess", proxies
                        )

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_europe_pmc(self, doi, proxies=None):
        """尝试 Europe PMC"""
        try:
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{doi}&resulttype=core"
            response = self._try_with_fallback(url, timeout=10, proxies=proxies)

            if response.status_code == 200:
                pdf_pattern = re.compile(
                    r'openAccess="Y"[^>]*>([^<]+)</', re.IGNORECASE
                )
                matches = pdf_pattern.findall(response.text)

                for pdf_url in matches[:3]:
                    if pdf_url and "pdf" in pdf_url.lower():
                        return self._download_and_save(
                            pdf_url, doi, "EuropePMC", proxies
                        )

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_pubmed(self, doi, proxies=None):
        """尝试 PubMed (生物医学)"""
        try:
            url = f"https://pubmed.ncbi.nlm.nih.gov/?term={quote(doi)}"
            response = self._try_with_fallback(url, timeout=10, proxies=proxies)

            if response.status_code == 200:
                pdf_pattern = re.compile(
                    r'href=["\']([^"\']*\/pdf\/[^"\']*)["\']', re.IGNORECASE
                )
                pdf_links = pdf_pattern.findall(response.text)

                for pdf_url in pdf_links[:2]:
                    if "pdf" in pdf_url.lower():
                        return self._download_and_save(pdf_url, doi, "PubMed", proxies)

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_paperity(self, doi, proxies=None):
        """尝试 Paperity"""
        try:
            url = f"https://paperity.org/search/?q={quote(doi)}"
            response = self.session.get(url, timeout=10, proxies=proxies)

            pdf_pattern = re.compile(
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(response.text)

            if pdf_links:
                for pdf_url in pdf_links[:3]:
                    if pdf_url and "download" in pdf_url.lower():
                        return self._download_and_save(
                            pdf_url, doi, "Paperity", proxies
                        )

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_google_scholar(self, doi, proxies=None):
        """尝试 Google Scholar (需要绕过代理)"""
        try:
            url = f"https://scholar.google.com/scholar?q={quote(doi)}"
            response = self.session.get(
                url, timeout=15, proxies=self.get_proxy_config(use_china_network=True)
            )

            if response.status_code == 200:
                pdf_pattern = re.compile(
                    r'href=["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE
                )
                pdf_links = pdf_pattern.findall(response.text)

                for pdf_url in pdf_links[:2]:
                    if pdf_url and pdf_url.startswith("http"):
                        return self._download_and_save(
                            pdf_url,
                            doi,
                            "GoogleScholar",
                            self.get_proxy_config(use_china_network=True),
                        )

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_researchgate(self, doi, proxies=None):
        """尝试 ResearchGate (需要绕过代理)"""
        try:
            url = f"https://www.researchgate.net/search?q={quote(doi)}"
            response = self.session.get(
                url, timeout=15, proxies=self.get_proxy_config(use_china_network=True)
            )

            if response.status_code == 200:
                pdf_pattern = re.compile(
                    r'href=["\']([^"\']*\/fullText\/pdf\/[^"\']*)["\']', re.IGNORECASE
                )
                pdf_links = pdf_pattern.findall(response.text)

                for pdf_url in pdf_links[:2]:
                    if pdf_url:
                        return self._download_and_save(
                            pdf_url,
                            doi,
                            "ResearchGate",
                            self.get_proxy_config(use_china_network=True),
                        )

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_scihub(self, doi, proxies=None):
        """尝试 Sci-Hub 下载

        基于改进版测试实现（使用 BeautifulSoup + 新域名）
        """
        from bs4 import BeautifulSoup

        # 使用经过验证的域名列表
        scihub_domains = [
            "https://www.sci-hub.ren",  # ✅ 新域名
            "https://sci-hub.hk",  # ✅ 新域名
            "https://sci-hub.la",  # ✅ 新域名
            "https://sci-hub.cat",
            "https://sci-hub.se",
            "https://sci-hub.st",
            "https://sci-hub.ru",
            "https://sci-hub.wf",
            "https://sci-hub.yt",
            "https://sci-hub.do",
            "https://sci-hub.mksa.top",
            "https://sci-hub.wf",
            "https://www.tes1e.com",  # ✅ 新域名
        ]

        for domain in scihub_domains:
            try:
                url = f"{domain}/{doi.replace('/', '%2F')}"

                response = self._try_with_fallback(
                    url, timeout=30, proxies=proxies, allow_redirects=True
                )

                if response.status_code != 200:
                    continue

                # 使用 BeautifulSoup 解析 HTML
                soup = BeautifulSoup(response.text, "html.parser")

                # 方法1: 查找 embed 标签（参考 GitHub 实现）
                embed = soup.find("embed")
                if embed:
                    embed_src = str(embed.get("src", ""))
                    if embed_src and ".pdf" in embed_src:
                        print(f"    ✅ 找到 embed 标签，尝试下载...")

                        # 确保 URL 完整
                        if embed_src.startswith("//"):
                            embed_src = "https:" + embed_src
                        elif not embed_src.startswith("http"):
                            embed_src = urljoin(response.url, embed_src)

                        result = self._download_and_save(
                            embed_src, doi, "SciHub", proxies
                        )
                        if result.get("success"):
                            return result
                        else:
                            print(f"    ❌ embed 标签下载失败")

                # 方法2: 查找 iframe 标签
                iframe = soup.find("iframe")
                if iframe:
                    iframe_src = str(iframe.get("src", ""))
                    if iframe_src and ".pdf" in iframe_src:
                        print(f"    ✅ 找到 iframe 标签，尝试下载...")

                        if iframe_src.startswith("//"):
                            iframe_src = "https:" + iframe_src
                        elif not iframe_src.startswith("http"):
                            iframe_src = urljoin(response.url, iframe_src)

                        result = self._download_and_save(
                            iframe_src, doi, "SciHub", proxies
                        )
                        if result.get("success"):
                            return result
                        else:
                            print(f"    ❌ iframe 标签下载失败")

                # 方法3: 查找所有 PDF 链接
                pdf_links = soup.find_all("a", href=True)
                for link in pdf_links:
                    href = str(link.get("href", ""))
                    if (
                        href
                        and ".pdf" in href.lower()
                        and "sci-hub" not in href.lower()
                    ):
                        if not href.startswith("http"):
                            href = urljoin(response.url, href)

                        result = self._download_and_save(href, doi, "SciHub", proxies)
                        if result.get("success"):
                            return result

                # 方法4: 检查是否直接是 PDF 响应
                content_type = response.headers.get("Content-Type", "").lower()
                if "pdf" in content_type:
                    filename = f"SciHub_{doi.replace('/', '_').replace('.', '_')}.pdf"
                    filepath = os.path.join(self.output_dir, filename)

                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    file_size = os.path.getsize(filepath)

                    print(f"    📁 {filename} ({file_size:,} bytes)")

                    return {"success": True, "file": filepath, "size": file_size}

            except requests.exceptions.RequestException:
                continue
            except Exception as e:
                continue

        return {"success": False}

    def _download_and_save(self, url, doi, source, proxies=None):
        """下载并保存 PDF"""
        try:
            response = self.session.get(url, timeout=30, stream=True, proxies=proxies)

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()

                if "pdf" in content_type or url.lower().endswith(".pdf"):
                    # 使用新的文件名生成逻辑
                    filename = self.generate_filename(doi, source) + ".pdf"
                    filepath = os.path.join(self.output_dir, filename)

                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    file_size = os.path.getsize(filepath)

                    print(f"    📁 {filename} ({file_size:,} bytes)")

                    return {"success": True, "file": filepath, "size": file_size}

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_download_from_ris(self, ris_file):
        """从 RIS 文件批量下载 (并发)"""

        print("=" * 70)
        print("📚 RIS 文件多渠道批量下载器 v3.0 (增强版)")
        print("=" * 70)
        print(f"\n📄 RIS 文件: {ris_file}")

        # 解析 RIS 元数据
        print("📖 解析 RIS 元数据...")
        self.doi_metadata = self.parse_ris_metadata(ris_file)
        print(f"   ✅ 解析完成，共 {len(self.doi_metadata)} 条元数据")

        dois = list(self.doi_metadata.keys())
        print(f"\n📋 找到 {len(dois)} 个 DOI:")
        for i, doi in enumerate(dois, 1):
            metadata = self.doi_metadata.get(doi, {})
            print(f"  [{i}] {doi}")
            print(
                f"      {metadata.get('year', 'N/A')} - {metadata.get('journal', 'N/A')} - {metadata.get('first_author', 'N/A')}"
            )

        print(f"\n🚀 开始并发下载 (最大并发数: {self.max_workers})")
        print(f"🔧 最大重试次数: {self.max_retries}")
        print(f"📁 保存目录: {self.output_dir}")
        print("=" * 70)

        self.html_report["total"] = len(dois)

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
                    print(f"❌ [{idx + 1}] {doi} 发生异常: {e}")
                    with self.lock:
                        self.results["failed"].append(doi)

        self.html_report["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.html_report["success"] = len(self.results["success"])
        self.html_report["failed"] = len(self.results["failed"])

        self.print_summary(dois)
        self.generate_html_report()

    def print_summary(self, dois):
        """打印下载总结"""
        print("\n" + "=" * 70)
        print("📊 下载总结")
        print("=" * 70)

        print(f"\n✅ 成功: {len(self.results['success'])} 篇")
        for item in self.results["success"]:
            print(f"   ✓ {item['doi']}")
            print(f"     来源: {item['source']} (重试{item.get('retry', 0)}次)")
            print(f"     文件: {item['file']}")

        print(f"\n❌ 失败: {len(self.results['failed'])} 篇")
        for doi in self.results["failed"]:
            print(f"   ✗ {doi}")

        success_rate = len(self.results["success"]) / len(dois) * 100
        print(f"\n📈 成功率: {success_rate:.1f}%")

        log_file = os.path.join(self.output_dir, "download_summary.txt")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"RIS 文件批量下载总结 (v3.0 增强版)\n")
            f.write(
                f"时间: {self.html_report['start_time']} - {self.html_report['end_time']}\n"
            )
            f.write(f"总计: {len(dois)} 篇\n")
            f.write(f"成功: {len(self.results['success'])} 篇\n")
            f.write(f"失败: {len(self.results['failed'])} 篇\n")
            f.write(f"成功率: {success_rate:.1f}%\n")
            f.write(f"最大重试次数: {self.max_retries}\n\n")

            f.write("成功列表:\n")
            for item in self.results["success"]:
                f.write(f"  {item['doi']}\n")
                f.write(f"    来源: {item['source']}\n")
                f.write(f"    文件: {item['file']}\n\n")

            f.write("失败列表:\n")
            for doi in self.results["failed"]:
                f.write(f"  {doi}\n\n")

        print(f"\n📝 详细日志: {log_file}")

        print("\n" + "=" * 70)
        print("💡 手动下载建议")
        print("=" * 70)

        if self.results["failed"]:
            print("\n对于未下载的文献，可以尝试：")
            print("  1. Google Scholar: https://scholar.google.com/")
            print("  2. Sci-Hub: https://sci-hub.se/ (谨慎使用)")
            print("  3. ResearchGate: https://www.researchgate.net/")
            print("  4. 图书馆资源")
            print("  5. 联系作者")

    def generate_html_report(self):
        """生成 HTML 可视化报告"""
        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文献下载报告 - {self.html_report["start_time"]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .success .stat-value {{ color: #28a745; }}
        .failed .stat-value {{ color: #dc3545; }}
        .progress-bar {{
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            margin: 20px 30px;
            overflow: hidden;
            display: flex;
        }}
        .progress-fill {{
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.5s ease;
        }}
        .progress-fill.success {{
            background: linear-gradient(90deg, #28a745, #34d399);
        }}
        .progress-fill.failed {{
            background: linear-gradient(90deg, #dc3545, #f87171);
        }}
        .items {{
            padding: 30px;
        }}
        .items h2 {{
            margin-bottom: 20px;
            color: #333;
        }}
        .item {{
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s;
        }}
        .item:hover {{
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border-color: #667eea;
        }}
        .item.success {{
            border-left: 5px solid #28a745;
        }}
        .item.failed {{
            border-left: 5px solid #dc3545;
        }}
        .item-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .item-doi {{
            font-weight: bold;
            font-size: 1.1em;
            color: #333;
        }}
        .item-status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .item-status.success {{
            background: #d4edda;
            color: #155724;
        }}
        .item-status.failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .item-details {{
            font-size: 0.9em;
            color: #6c757d;
            line-height: 1.6;
        }}
        .attempt-log {{
            margin-top: 10px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            font-size: 0.85em;
        }}
        .attempt {{
            margin: 5px 0;
            padding: 5px;
            background: white;
            border-radius: 3px;
        }}
        .attempt.success {{
            border-left: 3px solid #28a745;
        }}
        .attempt.failed {{
            border-left: 3px solid #dc3545;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            margin-right: 5px;
            background: #e9ecef;
        }}
        .badge.source {{
            background: #007bff;
            color: white;
        }}
        .badge.retry {{
            background: #ffc107;
            color: #333;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9em;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .item {{
            animation: fadeIn 0.5s ease forwards;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 文献下载报告</h1>
            <p class="subtitle">v3.0 增强版 - {self.html_report["start_time"]}</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{self.html_report["total"]}</div>
                <div class="stat-label">总文献数</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">{self.html_report["success"]}</div>
                <div class="stat-label">成功下载</div>
            </div>
            <div class="stat-card failed">
                <div class="stat-value">{self.html_report["failed"]}</div>
                <div class="stat-label">下载失败</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{self.html_report["success"] / self.html_report["total"] * 100:.1f}%</div>
                <div class="stat-label">成功率</div>
            </div>
        </div>

        <div class="progress-bar">
            <div class="progress-fill success" style="width: {self.html_report["success"] / self.html_report["total"] * 100}%">
                {self.html_report["success"]} 成功
            </div>
            <div class="progress-fill failed" style="width: {self.html_report["failed"] / self.html_report["total"] * 100}%">
                {self.html_report["failed"]} 失败
            </div>
        </div>

        <div class="items">
            <h2>📋 下载详情</h2>
"""

        for i, item in enumerate(self.html_report["items"]):
            status_class = item.get("status", "failed")
            status_text = "✅ 成功" if item["status"] == "success" else "❌ 失败"

            html_template += f"""
            <div class="item {status_class}" style="animation-delay: {i * 0.1}s">
                <div class="item-header">
                    <span class="item-doi">[{item["index"]}] {item["doi"]}</span>
                    <span class="item-status {status_class}">{status_text}</span>
                </div>
                <div class="item-details">
"""

            if item["status"] == "success":
                html_template += f"""
                    <p><strong>下载来源:</strong> <span class="badge source">{item["final_source"]}</span></p>
                    <p><strong>文件路径:</strong> {item["file"]}</p>
                    <p><strong>文件大小:</strong> {item["size"]:,} bytes ({item["size"] / 1024:.1f} KB)</p>
"""

            if item["attempts"]:
                html_template += f"""
                    <div class="attempt-log">
                        <strong>尝试记录:</strong>
"""
                for attempt in item["attempts"]:
                    attempt_status = "✅" if attempt["status"] == "success" else "❌"
                    html_template += f"""
                        <div class="attempt {attempt["status"]}">
                            {attempt_status} <span class="badge source">{attempt["source"]}</span>
                            <span class="badge retry">重试 #{attempt["retry"]}</span>
                            {attempt["status"]}
                        </div>
"""
                html_template += """
                    </div>
"""

            html_template += """
                </div>
            </div>
"""

        html_template += f"""
        </div>

        <div class="footer">
            <p>📅 生成时间: {self.html_report["end_time"]}</p>
            <p>🚀 使用多源并发下载 | 最大重试次数: {self.max_retries} | 并发数: {self.max_workers}</p>
        </div>
    </div>
</body>
</html>
"""

        html_file = os.path.join(self.output_dir, "download_report.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_template)

        print(f"\n🌐 HTML 可视化报告: {html_file}")


def main():
    """主函数"""
    ris_file = "/Users/sanada/Desktop/20260129 博士课题探索/Script /04_PaperDownloader/savedrecs.ris"

    if len(sys.argv) > 1:
        ris_file = sys.argv[1]

    if not os.path.exists(ris_file):
        print(f"❌ 文件不存在: {ris_file}")
        print("\n使用方法:")
        print("  python3 multi_source_ris_downloader_v3.py [ris_file]")
        print("\n可选参数:")
        print("  --workers N: 设置并发数 (默认: 3)")
        print("  --retries N: 设置重试次数 (默认: 2)")
        print("\n示例:")
        print("  python3 multi_source_ris_downloader_v3.py savedrecs.ris")
        print(
            "  python3 multi_source_ris_downloader_v3.py savedrecs.ris --workers 5 --retries 3"
        )
        sys.exit(1)

    max_workers = 3
    max_retries = 2

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--workers" and i + 1 < len(args):
            max_workers = int(args[i + 1])
            i += 2
        elif args[i] == "--retries" and i + 1 < len(args):
            max_retries = int(args[i + 1])
            i += 2
        else:
            i += 1

    downloader = MultiSourceDownloader(max_workers=max_workers, max_retries=max_retries)
    downloader.batch_download_from_ris(ris_file)


if __name__ == "__main__":
    main()
