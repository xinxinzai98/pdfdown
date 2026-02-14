#!/usr/bin/env python3
"""
测试带 Headers 的 PDF 下载
"""

import requests
import os

os.environ["NO_PROXY"] = "*"

pdf_url = "https://www.mdpi.com/2227-9717/8/2/248/pdf?version=1582684442"
output_dir = "ris_downloads"
doi = "10.3390/pr8020248"
source = "Test"

print("=" * 70)
print("测试带 Headers 的 PDF 下载")
print("=" * 70)
print(f"PDF URL: {pdf_url}")
print(f"DOI: {doi}")
print(f"保存目录: {output_dir}")
print()

# 创建 session 并禁用系统代理
session = requests.Session()
session.trust_env = False

# 添加 headers
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://doi.org/10.3390/pr8020248",
        "Connection": "keep-alive",
    }
)

print("正在下载 PDF...")
response = session.get(pdf_url, timeout=30, stream=True)

print(f"状态码: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")

if response.status_code == 200:
    content_type = response.headers.get("Content-Type", "").lower()

    print(f"内容长度: {len(response.content)}")

    if "pdf" in content_type or pdf_url.lower().endswith(".pdf"):
        safe_doi = doi.replace("/", "_").replace(".", "_")
        filename = f"{source}_{safe_doi}.pdf"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(filepath)

        print(f"\n✅ 下载成功!")
        print(f"文件名: {filename}")
        print(f"文件路径: {filepath}")
        print(f"文件大小: {file_size:,} bytes")
    else:
        print(f"❌ 不是 PDF 文件")
        print(f"响应前 200 字符: {response.text[:200]}")
else:
    print("❌ 下载失败")
    print(f"响应: {response.text[:200]}")
