#!/usr/bin/env python3
import requests
import re
import os
import urllib.parse
import json
from urllib.parse import urlparse


def search_and_download_pdf(doi, output_dir="downloads"):
    """Search DOI on open-access.shop and download PDF

    Args:
        doi: The DOI to search for
        output_dir: Directory to save PDF files
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    session = requests.Session()
    # 禁用代理（避免使用系统代理设置）
    session.trust_env = False
    session.proxies = {
        "http": None,
        "https": None,
    }

    print("🔒 已禁用代理设置（不使用系统代理）")

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Referer": "https://www.open-access.shop/",
            "Origin": "https://www.open-access.shop",
            "X-Requested-With": "XMLHttpRequest",
        }
    )

    base_url = "https://www.open-access.shop/"

    print(f"Searching for DOI: {doi}")
    print("=" * 60)

    possible_endpoints = [
        f"?get={urllib.parse.quote(doi)}",
        f"?search={urllib.parse.quote(doi)}",
        f"?q={urllib.parse.quote(doi)}",
        f"?w={urllib.parse.quote(doi)}",
        f"?doi={urllib.parse.quote(doi)}",
        f"/search?q={urllib.parse.quote(doi)}",
        f"/search?get={urllib.parse.quote(doi)}",
    ]

    for endpoint in possible_endpoints:
        url = base_url + endpoint.lstrip("/")
        print(f"\nTrying endpoint: {url}")

        try:
            response = session.get(url, timeout=30)
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('Content-Type', 'N/A')}")

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()

                if "json" in content_type:
                    try:
                        data = response.json()
                        print(
                            f"  JSON response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
                        )
                        print(
                            f"  Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}"
                        )
                    except:
                        print(f"  Response: {response.text[:500]}")
                else:
                    print(f"  Response length: {len(response.text)}")

                    pdf_links = extract_pdf_links(response.text, base_url)
                    cloud_links = extract_cloud_links(response.text)

                    if pdf_links:
                        print(f"\n  Found {len(pdf_links)} PDF link(s):")
                        for link in pdf_links:
                            print(f"    - {link}")

                    if cloud_links:
                        print(f"\n  Found {len(cloud_links)} cloud storage link(s):")
                        for link in cloud_links:
                            print(f"    - {link}")

                    save_debug_html(
                        response.text,
                        output_dir,
                        f"debug_{endpoint.replace('/', '_').replace('?', '_')}.html",
                    )

                    if pdf_links:
                        for pdf_url in pdf_links:
                            try:
                                print(f"\n  Attempting to download: {pdf_url}")
                                pdf_response = session.get(
                                    pdf_url, timeout=60, stream=True
                                )
                                pdf_response.raise_for_status()

                                filename = f"{output_dir}/{doi.replace('/', '_').replace('.', '_')}.pdf"
                                with open(filename, "wb") as f:
                                    for chunk in pdf_response.iter_content(
                                        chunk_size=8192
                                    ):
                                        f.write(chunk)

                                file_size = os.path.getsize(filename)
                                print(
                                    f"  ✓ PDF saved to: {filename} ({file_size} bytes)"
                                )
                                return filename
                            except Exception as e:
                                print(f"  ✗ Failed to download {pdf_url}: {e}")
                                continue

                    if (
                        "warning" in response.text.lower()
                        or "not supported" in response.text.lower()
                    ):
                        print("\n  ⚠ Warning detected: IP or region may be blocked")
                        print("    The website may have geo-restrictions")

        except Exception as e:
            print(f"  Error: {e}")
            continue

    print("\n" + "=" * 60)
    print("⚠️  检测到地理位置限制")
    print("=" * 60)
    print("\n网站提示: Access is not supported in your region")
    print("\n这意味着:")
    print("  ✗ 您的IP地址被识别为中国以外区域")
    print("  ✓ 但您仍可以通过云盘链接下载！")
    print("\n解决方案:")
    print("\n【方法一】手动下载（推荐，无需代理）:")
    print("  1. 访问: https://www.open-access.shop/")
    print(f"  2. 搜索: {doi}")
    print("  3. 在弹出的窗口中选择右侧的云盘下载选项")
    print("  4. 从云盘下载PDF")
    print("\n【方法二】查看调试文件:")
    print(f"  1. 打开文件: {output_dir}/debug_*.html")
    print("  2. 在浏览器中打开")
    print("  3. 查找云盘链接（189云盘、123云盘等）")
    print("  4. 复制链接手动下载")
    print("\n【方法三】使用代理:")
    print('  export HTTPS_PROXY="http://your-proxy:port"')
    print('  python3 open_access_downloader.py "your-doi"')

    return None


def extract_pdf_links(html, base_url):
    """Extract PDF links from HTML"""
    pdf_links = []

    patterns = [
        r'https?://[^\s"\'>]+\.(?:pdf)',
        r'"url"\s*:\s*"([^"]*\.pdf[^"]*)"',
        r'"link"\s*:\s*"([^"]*\.pdf[^"]*)"',
        r'"download"\s*:\s*"([^"]*\.pdf[^"]*)"',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match else ""

            if match and match not in pdf_links:
                if match.startswith("//"):
                    match = "https:" + match
                elif not match.startswith("http"):
                    match = urllib.parse.urljoin(base_url, match)

                pdf_links.append(match)

    return pdf_links


def extract_cloud_links(html):
    """Extract cloud storage links from HTML"""
    cloud_domains = [
        "cloud.189.cn",
        "123pan.com",
        "pan.quark.cn",
        "pan.baidu.com",
        "epicgames.com",
        "92.223.124.29",
    ]

    cloud_links = []

    for domain in cloud_domains:
        pattern = rf'https?://[^\s"\'>]*{re.escape(domain)}[^\s"\'>]*'
        matches = re.findall(pattern, html, re.IGNORECASE)

        for match in matches:
            if match not in cloud_links:
                cloud_links.append(match)

    return cloud_links


def save_debug_html(html, output_dir, filename):
    """Save HTML content for debugging"""
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Debug saved: {filepath}")


if __name__ == "__main__":
    doi = "10.1016/j.apenergy.2025.126643"

    import sys

    if len(sys.argv) > 1:
        doi = sys.argv[1]

    output_dir = sys.argv[2] if len(sys.argv) > 2 else "downloads"

    result = search_and_download_pdf(doi, output_dir)

    if result:
        print(f"\n✓ Success! PDF downloaded to: {result}")
    else:
        print(f"\n✗ Failed. Check the {output_dir} directory for debug files.")
