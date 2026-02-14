#!/usr/bin/env python3
"""
测试网络连接
"""

import requests
import os

os.environ["NO_PROXY"] = "*"

# 测试 Unpaywall API
url = "https://api.unpaywall.org/v2/10.3390/pr8020248?email=894643096@qq.com"

print("=" * 70)
print("测试网络连接")
print("=" * 70)
print(f"测试 URL: {url}")
print()

session = requests.Session()
session.trust_env = False

try:
    response = session.get(url, timeout=10)
    print(f"✅ Unpaywall API 连接成功")
    print(f"   状态码: {response.status_code}")
    print(f"   响应长度: {len(response.text)}")
except Exception as e:
    print(f"❌ Unpaywall API 连接失败: {e}")

print()

# 测试 Sci-Hub 域名
scihub_domains = [
    "https://www.sci-hub.ren",
    "https://sci-hub.hk",
    "https://sci-hub.la",
]

print("测试 Sci-Hub 域名连接:")
for domain in scihub_domains[:2]:  # 只测试前 2 个
    try:
        response = session.get(domain, timeout=10)
        print(f"✅ {domain} - 状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ {domain} - 失败: {str(e)[:50]}")

print("=" * 70)
