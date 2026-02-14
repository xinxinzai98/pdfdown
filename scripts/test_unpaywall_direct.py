#!/usr/bin/env python3
"""
直接测试 Unpaywall API
"""

import requests
import json

doi = "10.1002/adma.202520491"

print(f"测试 Unpaywall API: {doi}")
print()

url = f"https://api.unpaywall.org/v2/{doi}?email=894643096@qq.com"

print(f"请求 URL: {url}")
print("正在请求...")

# 创建 session 并禁用系统代理
session = requests.Session()
session.trust_env = False  # 禁用系统代理

response = session.get(url, timeout=10)

print(f"状态码: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
else:
    print(f"失败: {response.text[:200]}")
