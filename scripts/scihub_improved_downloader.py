#!/usr/bin/env python3
"""
Sci-Hub 改进版下载测试器
基于 GitHub 上的实现方式
"""

import os
import re
import time
from urllib.parse import urljoin
import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("错误: 未安装 BeautifulSoup4")
    print("请运行: pip3 install beautifulsoup4")
    sys.exit(1)


class SciHubImprovedDownloader:
    """改进版 Sci-Hub 下载器"""

    def __init__(self, output_dir="ris_downloads"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 使用 GitHub 实现中的新域名
        self.scihub_domains = [
            "https://www.sci-hub.ren",  # 新域名 ✅ 可用
            "https://sci-hub.hk",
            "https://sci-hub.la",  # 新域名 ✅ 可用
            "https://sci-hub.cat",
            "https://sci-hub.ee",
            "https://sci-hub.se",
            "https://sci-hub.st",
            "https://sci-hub.ru",
            "sci-hub.wf",
            "sci-hub.yt",
            "sci-hub.do",
            "https://sci-hub.mksa.top",
            "https://www.tes1e.com",  # 新域名
        ]

        # 使用 Windows User-Agent（参考 GitHub 实现）
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # 使用海外代理
        self.proxies = {
            "http": "http://127.0.0.1:7897",
            "https": "http://127.0.0.1:7897",
        }

    def download(self, doi):
        """从 Sci-Hub 下载文献"""

        print(f"\\n尝试下载: {doi}")

        for domain in self.scihub_domains:
            try:
                url = f"{domain}/{doi.replace('/', '%2F')}"
                print(f"\\n域名: {domain}")
                print(f"URL: {url}")

                response = self.session.get(
                    url, proxies=self.proxies, timeout=30, allow_redirects=True
                )
                print(f"  状态码: {response.status_code}")

                if response.status_code != 200:
                    print(f"  ❌ 状态码错误")
                    continue

                # 使用 BeautifulSoup 解析
                soup = BeautifulSoup(response.text, "html.parser")

                # 检查是否被 DDoS-Guard 保护
                if "DDoS-Guard" in response.text:
                    print(f"  ❌ 被 DDoS-Guard 保护")
                    continue

                # 方法1: 查找 embed 标签（GitHub 方法）
                embed = soup.find("embed")
                if embed:
                    embed_src = embed.get("src", "")
                    if embed_src:
                        embed_src_str = str(embed_src)
                        print(f"  ✓ 找到 embed 标签")
                        print(f"    src: {embed_src_str[:80]}...")

                        # 确保 URL 是完整的
                        if embed_src_str.startswith("//"):
                            embed_src_str = "https:" + embed_src_str
                        elif not embed_src_str.startswith("http"):
                            embed_src_str = urljoin(response.url, embed_src_str)

                        # 尝试下载
                        result = self._download_pdf(embed_src_str, doi)
                        if result["success"]:
                            return result
                        else:
                            print(f"    ❌ 下载失败")

                # 方法2: 查找 iframe 标签
                iframe = soup.find("iframe")
                if iframe:
                    iframe_src = iframe.get("src", "")
                    if iframe_src:
                        iframe_src_str = str(iframe_src)
                        print(f"  ✓ 找到 iframe 标签")
                        print(f"    src: {iframe_src_str[:80]}...")

                        # 确保 URL 是完整的
                        if iframe_src_str.startswith("//"):
                            iframe_src_str = "https:" + iframe_src_str
                        elif not iframe_src_str.startswith("http"):
                            iframe_src_str = urljoin(response.url, iframe_src_str)

                        result = self._download_pdf(iframe_src_str, doi)
                        if result["success"]:
                            return result
                        else:
                            print(f"    ❌ 下载失败")

                # 方法3: 查找所有 PDF 链接
                pdf_links = soup.find_all("a", href=True)
                pdf_links = [
                    l
                    for l in pdf_links
                    if l.get("href") and ".pdf" in str(l.get("href", ""))
                ]

                if pdf_links:
                    print(f"  ✓ 找到 {len(pdf_links)} 个 PDF 链接")

                    for i, link in enumerate(pdf_links[:3], 1):
                        href = link.get("href", "")
                        if href and "sci-hub" not in href.lower():
                            href_str = str(href)
                            if not href_str.startswith("http"):
                                href_str = urljoin(response.url, href_str)

                            result = self._download_pdf(href_str, doi)
                            if result["success"]:
                                return result
                            else:
                                print(f"    [{i}] 下载失败")

                print(f"  ❌ 未找到可下载的 PDF")

            except Exception as e:
                print(f"  ❌ 错误: {str(e)[:80]}")
                continue

        return {"success": False, "error": "所有域名均失败"}

    def _download_pdf(self, pdf_url, doi):
        """下载 PDF"""
        try:
            response = self.session.get(
                pdf_url, proxies=self.proxies, timeout=30, stream=True
            )

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()

                if "pdf" in content_type or pdf_url.lower().endswith(".pdf"):
                    safe_doi = doi.replace("/", "_").replace(".", "_")
                    filename = f"SciHub_{safe_doi}.pdf"
                    filepath = os.path.join(self.output_dir, filename)

                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    file_size = os.path.getsize(filepath)

                    print(f"    ✅ 下载成功!")
                    print(f"    文件: {filename}")
                    print(f"    大小: {file_size:,} bytes")

                    # 验证 PDF
                    with open(filepath, "rb") as f:
                        header = f.read(4)
                        tail = f.read()[-100:]

                    if header == b"%PDF" and b"%EOF" in tail:
                        print(f"    ✅ PDF 验证通过")
                    else:
                        print(f"    ⚠️ PDF 可能损坏")

                    return {"success": True, "file": filepath, "size": file_size}

            return {"success": False}

        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    """主函数"""
    import sys

    doi = "10.3390/pr8020248"

    if len(sys.argv) > 1:
        doi = sys.argv[1]

    print("=" * 70)
    print("🧪 Sci-Hub 改进版下载器")
    print("=" * 70)

    downloader = SciHubImprovedDownloader()

    start = time.time()
    result = downloader.download(doi)
    elapsed = time.time() - start

    print(f"\\n总耗时: {elapsed:.1f} 秒")

    print("\\n" + "=" * 70)
    if result["success"]:
        print("✅ 下载成功!")
        print(f"文件: {result['file']}")
        print(f"大小: {result['size']:,} bytes")
    else:
        print("❌ 下载失败")
        if "error" in result:
            print(f"错误: {result['error']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
