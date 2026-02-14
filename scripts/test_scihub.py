#!/usr/bin/env python3
"""
Sci-Hub 下载测试脚本

测试 Sci-Hub 下载功能是否正常工作
"""

import re
import os
import requests
from urllib.parse import urljoin


def test_scihub(doi):
    """测试 Sci-Hub 下载"""

    print("=" * 70)
    print("🧪 Sci-Hub 下载测试")
    print("=" * 70)
    print(f"\nDOI: {doi}\n")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    )

    scihub_domains = [
        "https://sci-hub.se",
        "https://sci-hub.st",
        "https://sci-hub.ru",
        "https://sci-hub.wf",
        "https://sci-hub.yt",
    ]

    for domain in scihub_domains:
        print(f"\n尝试域名: {domain}")
        print("-" * 70)

        try:
            url = f"{domain}/{doi.replace('/', '%2F')}"
            print(f"  URL: {url}")

            response = session.get(url, timeout=30, allow_redirects=True)

            print(f"  状态码: {response.status_code}")
            print(f"  最终URL: {response.url}")
            print(f"  Content-Type: {response.headers.get('Content-Type', 'N/A')}")

            # 查找 PDF 链接
            pdf_pattern = re.compile(
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(response.text)

            if pdf_links:
                print(f"  ✓ 找到 {len(pdf_links)} 个 PDF 链接")
                for pdf_url in pdf_links[:3]:
                    print(f"    - {pdf_url}")

                    if not pdf_url.startswith("http"):
                        pdf_url = urljoin(response.url, pdf_url)

                    if pdf_url != "#" and "sci-hub" not in pdf_url.lower():
                        print(f"\n  尝试下载: {pdf_url}")

                        try:
                            pdf_response = session.get(pdf_url, timeout=30, stream=True)

                            if pdf_response.status_code == 200:
                                content_type = pdf_response.headers.get(
                                    "Content-Type", ""
                                ).lower()

                                if "pdf" in content_type:
                                    filename = f"SciHub_test_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                    filepath = os.path.join("test_download", filename)

                                    if not os.path.exists("test_download"):
                                        os.makedirs("test_download")

                                    with open(filepath, "wb") as f:
                                        for chunk in pdf_response.iter_content(
                                            chunk_size=8192
                                        ):
                                            f.write(chunk)

                                    file_size = os.path.getsize(filepath)

                                    print(f"\n  ✅ 下载成功!")
                                    print(f"     文件: {filepath}")
                                    print(
                                        f"     大小: {file_size:,} bytes ({file_size / 1024:.1f} KB)"
                                    )

                                    return True
                                else:
                                    print(
                                        f"     ❌ 不是 PDF (Content-Type: {content_type})"
                                    )

                        except Exception as e:
                            print(f"     ❌ 下载失败: {e}")

                # 找到链接后就不再尝试其他方法
                print(f"\n  ✅ {domain} 域名可用!")
                return True

            # 检查是否直接是 PDF
            content_type = response.headers.get("Content-Type", "").lower()

            if "pdf" in content_type:
                print(f"  ✓ 响应直接是 PDF")

                filename = f"SciHub_test_{doi.replace('/', '_').replace('.', '_')}.pdf"
                filepath = os.path.join("test_download", filename)

                if not os.path.exists("test_download"):
                    os.makedirs("test_download")

                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                file_size = os.path.getsize(filepath)

                print(f"  ✅ 下载成功!")
                print(f"     文件: {filepath}")
                print(f"     大小: {file_size:,} bytes ({file_size / 1024:.1f} KB)")

                return True

            # 查找嵌入的 PDF
            embed_pattern = re.compile(
                r'<embed[^>]*src=["\']([^"\']+)["\']', re.IGNORECASE
            )
            embed_matches = embed_pattern.findall(response.text)

            if embed_matches:
                print(f"  ✓ 找到 {len(embed_matches)} 个嵌入的 PDF")

                for embed_url in embed_matches:
                    if embed_url.endswith(".pdf"):
                        if embed_url.startswith("//"):
                            embed_url = "https:" + embed_url
                        elif not embed_url.startswith("http"):
                            embed_url = urljoin(domain, embed_url)

                        print(f"\n  尝试下载嵌入 PDF: {embed_url}")

                        try:
                            pdf_response = session.get(
                                embed_url, timeout=30, stream=True
                            )

                            if pdf_response.status_code == 200:
                                filename = f"SciHub_test_{doi.replace('/', '_').replace('.', '_')}.pdf"
                                filepath = os.path.join("test_download", filename)

                                with open(filepath, "wb") as f:
                                    for chunk in pdf_response.iter_content(
                                        chunk_size=8192
                                    ):
                                        f.write(chunk)

                                file_size = os.path.getsize(filepath)

                                print(f"  ✅ 下载成功!")
                                print(f"     文件: {filepath}")
                                print(
                                    f"     大小: {file_size:,} bytes ({file_size / 1024:.1f} KB)"
                                )

                                return True

                        except Exception as e:
                            print(f"     ❌ 下载失败: {e}")

            print(f"  ⚠️ {domain} 未找到可下载的 PDF")

        except requests.exceptions.Timeout:
            print(f"  ⏱️ 超时 (30s)")
        except requests.exceptions.RequestException as e:
            print(f"  ❌ 网络错误: {e}")
        except Exception as e:
            print(f"  ❌ 其他错误: {e}")

        # 短暂延迟
        import time

        time.sleep(1)

    print("\n" + "=" * 70)
    print("❌ 所有 Sci-Hub 域名均无法下载该文献")
    print("=" * 70)
    print("\n可能原因:")
    print("  1. 该文献不在 Sci-Hub 数据库中")
    print("  2. 所有 Sci-Hub 域名当前均不可用")
    print("  3. 网络连接问题")
    print("  4. 文献需要付费墙，Sci-Hub 也无法绕过")

    return False


if __name__ == "__main__":
    import sys

    # 测试 DOI
    test_doi = "10.3390/pr8020248"

    if len(sys.argv) > 1:
        test_doi = sys.argv[1]

    success = test_scihub(test_doi)

    if success:
        print("\n✅ Sci-Hub 下载测试成功!")
    else:
        print("\n❌ Sci-Hub 下载测试失败")
