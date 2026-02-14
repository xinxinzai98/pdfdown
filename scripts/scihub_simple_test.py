#!/usr/bin/env python3
"""
Sci-Hub 简化测试版
基于 GitHub 上的实现方式
"""

import os
import requests
from bs4 import BeautifulSoup


def test_scihub_improved(doi, output_dir="ris_downloads"):
    """测试改进版 Sci-Hub 下载"""

    # 新域名列表（来自 GitHub 实现）
    scihub_domains = [
        "https://www.sci-hub.ren",  # 新域名 ✅
        "https://sci-hub.hk",  # 新域名 ✅
        "https://sci-hub.la",  # 新域名 ✅
        "https://sci-hub.cat",
        "https://sci-hub.ee",
        "https://sci-hub.se",
        "https://sci-hub.st",
        "https://sci-hub.ru",
        "sci-hub.wf",
        "sci-hub.yt",
        "sci-hub.do",
        "https://sci-hub.mksa.top",
        "https://www.tes1e.com",
    ]

    # Windows User-Agent（参考 GitHub）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # 代理配置
    proxies = {
        "http": "http://127.0.0.1:7897",
        "https": "http://127.0.0.1:7897",
    }

    print("=" * 70)
    print("🧪 Sci-Hub 简化测试版")
    print("=" * 70)
    print(f"DOI: {doi}")
    print()

    for domain in scihub_domains:
        try:
            url = f"{domain}/{doi.replace('/', '%2F')}"
            print(f"尝试域名: {domain}")

            response = requests.get(
                url, headers=headers, proxies=proxies, timeout=30, allow_redirects=True
            )
            print(f"  状态码: {response.status_code}")

            if response.status_code != 200:
                print(f"  ❌ 状态码错误")
                continue

            # 检查保护
            if "DDoS-Guard" in response.text:
                print(f"  ❌ 被 DDoS-Guard 保护")
                continue

            # 使用 BeautifulSoup 解析
            soup = BeautifulSoup(response.text, "html.parser")

            # 查找 embed 标签
            embed = soup.find("embed")
            if embed:
                embed_src = embed.get("src", "")
                if embed_src:
                    print(f"  ✅ 找到 embed 标签")
                    print(f"     src: {embed_src[:80]}...")

                    # 尝试下载
                    result = download_pdf(embed_src, doi, output_dir, headers, proxies)
                    if result["success"]:
                        print(f"\\n✅ 下载成功!")
                        return result
                    else:
                        print(f"  ❌ 下载失败")

            # 查找 iframe 标签
            iframe = soup.find("iframe")
            if iframe:
                iframe_src = iframe.get("src", "")
                if iframe_src:
                    print(f"  ✅ 找到 iframe 标签")
                    print(f"     src: {iframe_src[:80]}...")

                    result = download_pdf(iframe_src, doi, output_dir, headers, proxies)
                    if result["success"]:
                        print(f"\\n✅ 下载成功!")
                        return result
                    else:
                        print(f"  ❌ 下载失败")

            # 查找 PDF 链接
            pdf_links = soup.find_all("a", href=True)
            pdf_count = 0
            for link in pdf_links:
                href = link.get("href", "")
                if href and ".pdf" in href.lower() and "sci-hub" not in href.lower():
                    pdf_count += 1
                    if pdf_count <= 3:
                        print(f"  [{pdf_count}] {href[:80]}...")

                    result = download_pdf(href, doi, output_dir, headers, proxies)
                    if result["success"]:
                        print(f"\\n✅ 下载成功!")
                        return result
                    else:
                        print(f"  ❌ 下载失败")

            print(f"  ❌ 未找到可下载的 PDF")

        except Exception as e:
            print(f"  ❌ 错误: {str(e)[:80]}")
            continue

    return {"success": False, "error": "所有域名均失败"}


def download_pdf(pdf_url, doi, output_dir, headers, proxies):
    """下载 PDF"""
    try:
        response = requests.get(
            pdf_url, headers=headers, proxies=proxies, timeout=30, stream=True
        )

        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "").lower()

            if "pdf" in content_type or pdf_url.lower().endswith(".pdf"):
                safe_doi = doi.replace("/", "_").replace(".", "_")
                filename = f"SciHub_Improved_{safe_doi}.pdf"
                filepath = os.path.join(output_dir, filename)

                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                file_size = os.path.getsize(filepath)

                print(f"     ✅ 文件: {filename}")
                print(f"     大小: {file_size:,} bytes")

                return {"success": True, "file": filepath, "size": file_size}

            return {"success": False}

    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    import sys

    doi = "10.3390/pr8020248"

    if len(sys.argv) > 1:
        doi = sys.argv[1]

    print("=" * 70)
    print("🧪 Sci-Hub 简化测试版")
    print("=" * 70)
    print(f"DOI: {doi}")
    print()

    downloader_result = test_scihub_improved(doi)

    print("\\n" + "=" * 70)
    if downloader_result["success"]:
        print("✅ 下载成功!")
        print(f"文件: {downloader_result['file']}")
        print(f"大小: {downloader_result['size']:,} bytes")
    else:
        print("❌ 下载失败")
        if "error" in downloader_result:
            print(f"错误: {downloader_result['error']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
