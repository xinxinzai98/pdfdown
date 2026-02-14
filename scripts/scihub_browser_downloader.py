#!/usr/bin/env python3
"""
Sci-Hub 浏览器自动化下载器
使用 Selenium 绕过反爬虫保护
"""

import os
import sys
import time
import re
from urllib.parse import urljoin

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    print("错误: 缺少依赖")
    print(f"请运行: pip3 install selenium webdriver-manager")
    print(f"缺失的模块: {e}")
    sys.exit(1)


class SciHubBrowserDownloader:
    """使用浏览器自动化下载 Sci-Hub 文献"""

    def __init__(self, headless=True):
        """初始化浏览器下载器

        Args:
            headless: 是否使用无头模式
        """
        self.headless = headless
        self.output_dir = "ris_downloads"

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _create_driver(self):
        """创建 WebDriver（自动管理驱动，支持代理）"""
        options = Options()

        if self.headless:
            options.add_argument("--headless")

        # 添加其他优化选项
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # 设置 User-Agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # 添加代理支持
        # 注意: Chrome 不直接支持通过命令行设置代理，需要通过 Selenium 的代理配置
        # 但我们可以在下载 PDF 时使用代理

        # 使用 webdriver-manager 自动管理驱动
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(30)

        return driver

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

        driver = None

        try:
            driver = self._create_driver()

            for domain in scihub_domains:
                try:
                    print(f"\n尝试域名: {domain}")
                    url = f"{domain}/{doi.replace('/', '%2F')}"

                    print(f"  访问: {url}")

                    # 绕过代理访问 Sci-Hub 页面（让浏览器直接访问）
                    driver.get(url)

                    # 等待页面加载
                    print(f"  等待页面加载...")
                    time.sleep(3)  # 给 JavaScript 执行时间

                    # 等待页面完全加载
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )

                    # 获取页面 HTML
                    html = driver.page_source
                    current_url = driver.current_url

                    print(f"  当前 URL: {current_url}")
                    print(f"  页面长度: {len(html)} 字符")

                    # 检查是否是 DDoS-Guard 挑战页面
                    if "DDoS-Guard" in html:
                        print(f"  ❌ 被 DDoS-Guard 保护")
                        continue

                    # 检查是否直接是 PDF
                    content_type = self._get_content_type_from_driver(driver)
                    print(f"  Content-Type: {content_type}")

                    if "pdf" in content_type.lower() or current_url.lower().endswith(
                        ".pdf"
                    ):
                        print(f"  ✅ 检测到 PDF 直接响应")

                        # 直接下载 PDF
                        filename = f"SciHub_Browser_{doi.replace('/', '_').replace('.', '_')}.pdf"
                        filepath = os.path.join(self.output_dir, filename)

                        # 使用 requests 下载 PDF
                        import requests

                        proxies = {
                            "http": "http://127.0.0.1:7897",
                            "https": "http://127.0.0.1:7897",
                        }

                        response = requests.get(
                            current_url, proxies=proxies, timeout=30, stream=True
                        )

                        if response.status_code == 200:
                            with open(filepath, "wb") as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)

                            file_size = os.path.getsize(filepath)

                            print(f"  ✅ 下载成功!")
                            print(f"     文件: {filename}")
                            print(f"     大小: {file_size:,} bytes")

                            driver.quit()
                            return {
                                "success": True,
                                "file": filepath,
                                "size": file_size,
                            }

                    # 查找 PDF 链接
                    pdf_links = self._extract_pdf_links(html, current_url)

                    if pdf_links:
                        print(f"  ✅ 找到 {len(pdf_links)} 个 PDF 链接")

                        for i, pdf_url in enumerate(pdf_links[:3], 1):
                            print(f"  [{i}] {pdf_url}")

                            # 尝试下载
                            result = self._download_pdf(pdf_url, doi, f"SciHub_Browser")

                            if result["success"]:
                                driver.quit()
                                return result

                            time.sleep(1)

                    # 查找嵌入的 PDF
                    embed_pdfs = self._extract_embed_pdfs(html, domain)

                    if embed_pdfs:
                        print(f"  ✅ 找到 {len(embed_pdfs)} 个嵌入 PDF")

                        for i, pdf_url in enumerate(embed_pdfs[:2], 1):
                            print(f"  [{i}] {pdf_url}")

                            result = self._download_pdf(pdf_url, doi, f"SciHub_Browser")

                            if result["success"]:
                                driver.quit()
                                return result

                            time.sleep(1)

                    print(f"  ❌ 未找到可下载的 PDF")

                except Exception as e:
                    print(f"  ❌ 域名 {domain} 失败: {str(e)[:100]}")
                    continue

            driver.quit()
            return {"success": False, "error": "所有域名均失败"}

        except Exception as e:
            if driver:
                driver.quit()
            return {"success": False, "error": str(e)}

    def _get_content_type_from_driver(self, driver):
        """从 WebDriver 获取 Content-Type"""
        try:
            content_type = driver.execute_script(
                "return document.contentType || 'unknown';"
            )
            return content_type
        except:
            return "unknown"

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
    import sys

    doi = "10.3390/pr8020248"

    if len(sys.argv) > 1:
        doi = sys.argv[1]

    headless = True
    if len(sys.argv) > 2 and sys.argv[2] == "--show":
        headless = False

    print("=" * 70)
    print("🧪 Sci-Hub 浏览器自动化下载器")
    print("=" * 70)
    print(f"\nDOI: {doi}")
    print(f"无头模式: {'是' if headless else '否'}")

    downloader = SciHubBrowserDownloader(headless=headless)

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
