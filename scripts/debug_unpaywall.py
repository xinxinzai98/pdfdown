#!/usr/bin/env python3
"""
调试 Unpaywall 下载方法
"""

import requests
import os

os.environ["NO_PROXY"] = "*"

# 使用已知可以下载的 DOI（open access）
test_doi = "10.3390/pr8020248"

print("=" * 70)
print("调试 Unpaywall 下载")
print("=" * 70)
print(f"DOI: {test_doi}")
print()

# 创建 session 并禁用系统代理
session = requests.Session()
session.trust_env = False

# Unpaywall API 请求
url = f"https://api.unpaywall.org/v2/{test_doi}?email=894643096@qq.com"
print(f"请求 URL: {url}")
print("正在请求...")

response = session.get(url, timeout=10)
print(f"状态码: {response.status_code}")
print(f"响应长度: {len(response.text)}")
print(f"响应前 200 字符: {response.text[:200]}")

if response.status_code == 200:
    try:
        data = response.json()
        print(f"\n✅ JSON 解析成功")
        print(f"is_oa: {data.get('is_oa')}")
        print(f"best_oa_location: {data.get('best_oa_location', {})}")

        if data.get("is_oa"):
            pdf_url = data.get("best_oa_location", {}).get("url")
            print(f"PDF URL: {pdf_url}")
        else:
            print("❌ 非 open access")
    except Exception as e:
        print(f"❌ JSON 解析失败: {e}")
