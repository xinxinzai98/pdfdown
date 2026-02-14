#!/usr/bin/env python3
"""
Sci-Hub Playwright 下载器
使用 Playwright 绕过反爬虫保护
"""

import os
import sys
import time
import re
from urllib.parse import urljoin

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("错误: 未安装 Playwright")
    print("请运行: pip3 install playwright")
    print("然后运行: playwright install")
    sys.exit(1)


class SciHubPlaywrightDownloader:
    """使用 Playwright 下载 Sci-Hub 文献"""

    def __init__(self, headless=True):
        """初始化 Playwright 下载器

        Args:
            headless: 是否使用无头模式
        """
        self.headless = headless
        self.output_dir = "ris_downloads"

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def download_from_scihub(self, doi):
        """从 Sci-Hub 下载文献

        Args:
            doi: DOI

        Returns:
            dict: {"success": bool, "file": str, "size": int, "error": str}
        """
        scihub_domains = [
            "https://sci-hub.ru",
            "https://sci-hub.wf",
            "https://sci-hub.mksa.top",
            "https://sci-hub.st",
            "https://sci-hub.do",
        ]

        with sync_playwright() as p:
            browser = None

            try:
                # 启动浏览器
                browser = p.chromium.launch(headless=self.headless)

                # 创建新页面
                page = browser.new_page()

                # 设置 User-Agent
                page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )

                for domain in scihub_domains:
                    try:
                        print(f"\n尝试域名: {domain}")
                        url = f"{domain}/{doi.replace('/', '%2F')}"

                        print(f"  访问: {url}")

                        # 访问页面
                        page.goto(url, wait_until="dom", timeout=30000)

                        # 等待页面加载
                        print(f"  等待 JavaScript 执行...")
                        time.sleep(5)  # 给 JavaScript 足够时间执行

                        # 获取当前 URL
                        current_url = page.url
                        print(f"  当前 URL: {current_url}")

                        # 获取页面内容
                        html = page.content()
                        print(f"  页面长度: {len(html)} 字符")

                        # 检查是否是 DDoS-Guard 挑战页面
                        if "DDoS-Guard" in html:
                            print(f"  ❌ 被 DDoS-Guard 保护")
                            continue

                        # 检查页面是否有 PDF 内容
                        pdf_url = None

                        # 方法1: 查找 PDF 链接
                        pdf_links = self._extract_pdf_links(html, current_url)

                        if pdf_links:
                            print(f"  ✅ 找到 {len(pdf_links)} 个 PDF 链接")
                            for i, link in enumerate(pdf_links[:3], 1):
                                print(f"    [{i}] {link}")

                                # 尝试下载
                                result = self._download_pdf(
                                    link, doi, "Playwright_SciHub"
                                )

                                if result["success"]:
                                    browser.close()
                                    return result

                                time.sleep(1)

                        # 方法2: 查找嵌入的 PDF
                        embed_pdfs = self._extract_embed_pdfs(html, domain)

                        if embed_pdfs:
                            print(f"  ✅ 找到 {len(embed_pdfs)} 个嵌入 PDF")
                            for i, link in enumerate(embed_pdfs[:2], 1):
                                print(f"    [{i}] {link}")

                                result = self._download_pdf(
                                    link, doi, "Playwright_SciHub"
                                )

                                if result["success"]:
                                    browser.close()
                                    return result

                                time.sleep(1)

                        # 方法3: 检查当前页面是否是 PDF
                        if self._is_pdf_page(page):
                            print(f"  ✅ 当前页面是 PDF")

                            # 下载 PDF
                            result = self._download_pdf(
                                current_url, doi, "Playwright_SciHub"
                            )

                            if result["success"]:
                                browser.close()
                                return result

                        print(f"  ❌ 未找到可下载的 PDF")

                    except Exception as e:
                        print(f"  ❌ 域名 {domain} 失败: {str(e)[:100]}")
                        continue

                browser.close()
                return {"success": False, "error": "所有域名均失败"}

            except Exception as e:
                if browser:
                    browser.close()
                return {"success": False, "error": str(e)}

    def _is_pdf_page(self, page):
        """检查当前页面是否是 PDF"""
        try:
            # 检查页面标题或内容
            title = page.title()
            if title and "pdf" in title.lower():
                return True

            # 检查内容类型
            content = page.content()
            if "%PDF" in content[:500]:
                return True

            return False
        except:
            return False

    def _extract_pdf_links(self, html, base_url):
        """从 HTML 中提取 PDF 链接"""
        pdf_links = []

        # 方法1: href 属性
        pattern = re.compile(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE)
        matches = pattern.findall(html)

        for match in matches:
            if match and match != "#" and "sci-hub" not in match.lower():
                if not match.startswith("http"):
                    match = urljoin(base_url, match)
                pdf_links.append(match)

        # 方法2: onclick 事件
        pattern2 = re.compile(
            r'onclick=["\'][^"\']*location\s*=\s*[\'"]([^"\']+\.pdf[^"\']*)["\']',
            re.IGNORECASE,
        )
        matches2 = pattern2.findall(html)

        for match in matches2:
            if match and "sci-hub" not in match.lower():
                if not match.startswith("http"):
                    match = urljoin(base_url, match)
                pdf_links.append(match)

        return list(set(pdf_links))  # 去重

    def _extract_embed_pdfs(self, html, base_url):
        """从 HTML 中提取嵌入的 PDF"""
        embed_pdfs = []

        # 查找 embed 标签
        pattern = re.compile(r'<embed[^>]*src=["\']([^"\']+)["\']', re.IGNORECASE)
        matches = pattern.findall(html)

        for match in matches:
            if match and match.endswith(".pdf"):
                if match.startswith("//"):
                    match = "https:" + match
                elif not match.startswith("http"):
                    match = urljoin(base_url, match)
                embed_pdfs.append(match)

        return embed_pdfs

    def _download_pdf(self, url, doi, source):
        """下载 PDF"""
        import requests

        proxies = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

        try:
            response = requests.get(url, proxies=proxies, timeout=30, stream=True)

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()

                if "pdf" in content_type or url.lower().endswith(".pdf"):
                    safe_doi = doi.replace("/", "_").replace(".", "_")
                    filename = f"{source}_{safe_doi}.pdf"
                    filepath = os.path.join(self.output_dir, filename)

                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    file_size = os.path.getsize(filepath)

                    print(f"    ✅ 下载成功!")
                    print(f"       文件: {filename}")
                    print(f"       大小: {file_size:,} bytes")

                    return {"success": True, "file": filepath, "size": file_size}

            return {"success": False}

        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    """主函数"""
    doi = "10.3390/pr8020248"

    if len(sys.argv) > 1:
        doi = sys.argv[1]

    headless = True
    if len(sys.argv) > 2 and sys.argv[2] == "--show":
        headless = False

    print("=" * 70)
    print("🧪 Sci-Hub Playwright 下载器")
    print("=" * 70)
    print(f"\nDOI: {doi}")
    print(f"无头模式: {'是' if headless else '否'}")

    downloader = SciHubPlaywrightDownloader(headless=headless)

    print("\n开始下载...")
    print("=" * 70)

    result = downloader.download_from_scihub(doi)

    print("\n" + "=" * 70)
    if result["success"]:
        print("✅ 下载成功!")
        print(f"文件: {result['file']}")
        print(f"大小: {result['size']:,} bytes")
    else:
        print("❌ 下载失败!")
        if "error" in result:
            print(f"错误: {result['error']}")

    print("=" * 70)


if __name__ == "__main__":
    main()
