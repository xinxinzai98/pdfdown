#!/usr/bin/env python3
"""
RIS 文件多渠道批量下载器

支持多种下载源，提高成功率
"""

import re
import os
import sys
import time
import requests
from urllib.parse import quote, urljoin


class MultiSourceDownloader:
    """多来源下载器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

        self.output_dir = "ris_downloads"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.results = {"success": [], "failed": []}

    def download_doi(self, doi, source_name="auto"):
        """尝试从多个来源下载单个 DOI

        Args:
            doi: DOI
            source_name: 来源名称
        """
        sources = [
            ("Unpaywall API", self._try_unpaywall),
            ("Sci-Hub ⚠️", self._try_scihub),
            ("Semantic Scholar", self._try_semantic_scholar),
            ("arXiv", self._try_arxiv),
            ("CORE", self._try_core),
            ("Open Access Button", self._try_openaccess),
        ]

        for source_name, download_func in sources:
            try:
                print(f"  [{source_name}] ...", end=" ")
                result = download_func(doi)

                if result and result.get("success"):
                    print(f"✅ 成功")
                    self.results["success"].append(
                        {"doi": doi, "source": source_name, "file": result.get("file")}
                    )
                    return True
                else:
                    print(f"❌ 失败")

                # 短暂延迟
                time.sleep(0.5)

            except Exception as e:
                print(f"❌ 错误: {str(e)[:50]}")

        return False

    def _try_unpaywall(self, doi):
        """尝试 Unpaywall API"""
        try:
            url = f"https://api.unpaywall.org/v2/{doi}?email=your@email.com"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("is_oa"):
                    pdf_url = data.get("best_oa_location", {}).get("url")
                    if pdf_url:
                        return self._download_and_save(pdf_url, doi, "Unpaywall")

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_semantic_scholar(self, doi):
        """尝试 Semantic Scholar"""
        try:
            url = f"https://api.semanticscholar.org/v1/paper/DOI:{doi}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # 检查开放获取
                oa_pdf = data.get("openAccessPdf")
                if oa_pdf:
                    pdf_url = oa_pdf.get("url")
                    if pdf_url:
                        return self._download_and_save(pdf_url, doi, "Semantic_Scholar")

                # 检查来源
                sources = data.get("sources", [])
                for source in sources:
                    url = source.get("url")
                    if url and "pdf" in url.lower():
                        return self._download_and_save(url, doi, "Semantic_Scholar")

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_arxiv(self, doi):
        """尝试 arXiv"""
        # 检查是否是 arXiv 论文
        if "arxiv" not in doi.lower():
            return {"success": False}

        # 提取 arXiv ID
        arxiv_pattern = re.compile(r"(?:10\.\d+/)?arxiv\.?/?(\d+\.\d+)", re.IGNORECASE)
        match = arxiv_pattern.search(doi)

        if match:
            arxiv_id = match.group(1)
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            return self._download_and_save(pdf_url, doi, "arXiv")

        return {"success": False}

    def _try_core(self, doi):
        """尝试 CORE"""
        try:
            url = f"https://core.ac.uk/search?q={quote(doi)}"
            response = self.session.get(url, timeout=10)

            # 查找 PDF 链接
            pdf_pattern = re.compile(
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(response.text)

            if pdf_links:
                for pdf_url in pdf_links[:3]:
                    if pdf_url.startswith("https://core.ac.uk/download"):
                        return self._download_and_save(pdf_url, doi, "CORE")

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_openaccess(self, doi):
        """尝试开放获取按钮"""
        try:
            url = f"https://api.openaccessbutton.org/v2/{doi}?email=your@email.com"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("file_type") == "pdf":
                    pdf_url = data.get("file_url")
                    if pdf_url:
                        return self._download_and_save(pdf_url, doi, "OpenAccess")

            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _try_scihub(self, doi):
        """尝试 Sci-Hub 下载

        注意: Sci-Hub 存在法律风险，请谨慎使用
        """
        scihub_domains = [
            "https://sci-hub.se",
            "https://sci-hub.st",
            "https://sci-hub.ru",
            "https://sci-hub.wf",
            "https://sci-hub.yt",
            "https://sci-hub.do",
        ]

        for domain in scihub_domains:
            try:
                # 构建 Sci-Hub URL
                url = f"{domain}/{doi.replace('/', '%2F')}"

                response = self.session.get(url, timeout=30, allow_redirects=True)

                if response.status_code == 200:
                    # 查找 PDF 链接
                    # Sci-Hub 通常会在响应中直接显示 PDF，或提供下载链接

                    # 方法1: 查找 PDF 链接
                    pdf_pattern = re.compile(
                        r'href=["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE
                    )
                    pdf_links = pdf_pattern.findall(response.text)

                    for pdf_url in pdf_links:
                        if (
                            pdf_url
                            and pdf_url != "#"
                            and "sci-hub" not in pdf_url.lower()
                        ):
                            if not pdf_url.startswith("http"):
                                pdf_url = urljoin(response.url, pdf_url)

                            # 尝试下载
                            result = self._download_and_save(pdf_url, doi, "SciHub")
                            if result.get("success"):
                                return result

                    # 方法2: 检查响应是否直接是 PDF
                    content_type = response.headers.get("Content-Type", "").lower()

                    if "pdf" in content_type or url.lower().endswith(".pdf"):
                        # 保存 PDF
                        filename = (
                            f"SciHub_{doi.replace('/', '_').replace('.', '_')}.pdf"
                        )
                        filepath = os.path.join(self.output_dir, filename)

                        with open(filepath, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)

                        file_size = os.path.getsize(filepath)

                        print(f"    📁 {filename} ({file_size:,} bytes)")

                        return {"success": True, "file": filepath, "size": file_size}

                    # 方法3: 查找嵌入的 PDF
                    embed_pdf_pattern = re.compile(
                        r'<embed[^>]*src=["\']([^"\']+)["\']', re.IGNORECASE
                    )
                    embed_matches = embed_pdf_pattern.findall(response.text)

                    for embed_url in embed_matches:
                        if embed_url and embed_url.endswith(".pdf"):
                            if embed_url.startswith("//"):
                                embed_url = "https:" + embed_url
                            elif not embed_url.startswith("http"):
                                embed_url = urljoin(domain, embed_url)

                            result = self._download_and_save(embed_url, doi, "SciHub")
                            if result.get("success"):
                                return result

            except requests.exceptions.RequestException:
                continue
            except Exception as e:
                continue

        return {"success": False}

    def _download_and_save(self, url, doi, source):
        """下载并保存 PDF"""
        try:
            response = self.session.get(url, timeout=30, stream=True)

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()

                if "pdf" in content_type or url.lower().endswith(".pdf"):
                    # 生成文件名
                    safe_doi = doi.replace("/", "_").replace(".", "_")
                    filename = f"{source}_{safe_doi}.pdf"
                    filepath = os.path.join(self.output_dir, filename)

                    # 保存文件
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
        """从 RIS 文件批量下载"""

        # 提取所有 DOI
        dois = []
        with open(ris_file, "r", encoding="utf-8") as f:
            content = f.read()

        doi_pattern = re.compile(r"^DO\s*-\s*(.+)$", re.MULTILINE)
        matches = doi_pattern.findall(content)

        for doi in matches:
            doi = doi.strip()
            if doi and doi not in dois:
                dois.append(doi)

        print("=" * 70)
        print("📚 RIS 文件多渠道批量下载器")
        print("=" * 70)
        print(f"\n📄 RIS 文件: {ris_file}")
        print(f"📋 找到 {len(dois)} 个 DOI:")
        for i, doi in enumerate(dois, 1):
            print(f"  [{i}] {doi}")

        print(f"\n🚀 开始批量下载...")
        print(f"📁 保存目录: {self.output_dir}")
        print("=" * 70)

        # 批量下载
        for i, doi in enumerate(dois, 1):
            print(f"\n[{i}/{len(dois)}] {doi}")
            print("-" * 70)

            success = self.download_doi(doi)

            if success:
                print(f"✅ {doi} 下载成功")
            else:
                print(f"❌ {doi} 所有来源均失败")
                self.results["failed"].append(doi)

            # 延迟
            if i < len(dois):
                time.sleep(2)

        # 打印总结
        self.print_summary(dois)

    def print_summary(self, dois):
        """打印下载总结"""
        print("\n" + "=" * 70)
        print("📊 下载总结")
        print("=" * 70)

        print(f"\n✅ 成功: {len(self.results['success'])} 篇")
        for item in self.results["success"]:
            print(f"   ✓ {item['doi']}")
            print(f"     来源: {item['source']}")
            print(f"     文件: {item['file']}")

        print(f"\n❌ 失败: {len(self.results['failed'])} 篇")
        for doi in self.results["failed"]:
            print(f"   ✗ {doi}")

        success_rate = len(self.results["success"]) / len(dois) * 100
        print(f"\n📈 成功率: {success_rate:.1f}%")

        # 保存日志
        log_file = os.path.join(self.output_dir, "download_summary.txt")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"RIS 文件批量下载总结\n")
            f.write(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总计: {len(dois)} 篇\n")
            f.write(f"成功: {len(self.results['success'])} 篇\n")
            f.write(f"失败: {len(self.results['failed'])} 篇\n")
            f.write(f"成功率: {success_rate:.1f}%\n\n")

            f.write("成功列表:\n")
            for item in self.results["success"]:
                f.write(f"  {item['doi']}\n")
                f.write(f"    来源: {item['source']}\n")
                f.write(f"    文件: {item['file']}\n\n")

            f.write("失败列表:\n")
            for doi in self.results["failed"]:
                f.write(f"  {doi}\n\n")

        print(f"\n📝 详细日志: {log_file}")

        # 提供建议
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


def main():
    """主函数"""
    # 默认 RIS 文件
    ris_file = "/Users/sanada/downloads/savedrecs.ris"

    # 检查参数
    if len(sys.argv) > 1:
        ris_file = sys.argv[1]

    # 检查文件
    if not os.path.exists(ris_file):
        print(f"❌ 文件不存在: {ris_file}")
        print("\n使用方法:")
        print("  python3 multi_source_ris_downloader.py [ris_file]")
        print("\n示例:")
        print("  python3 multi_source_ris_downloader.py savedrecs.ris")
        sys.exit(1)

    # 创建下载器
    downloader = MultiSourceDownloader()

    # 批量下载
    downloader.batch_download_from_ris(ris_file)


if __name__ == "__main__":
    main()
