#!/usr/bin/env python3
"""
简单测试 - 测试代理连接和 API 可用性
"""

import requests
import time


def test_proxy_and_apis():
    """测试代理和 API 连接"""

    print("=" * 70)
    print("🧪 代理和 API 连接测试")
    print("=" * 70)

    proxies = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    tests = [
        (
            "Unpaywall API",
            "https://api.unpaywall.org/v2/10.3390/pr8020248?email=your@email.com",
            proxies,
        ),
        (
            "Semantic Scholar",
            "https://api.semanticscholar.org/v1/paper/DOI:10.3390/pr8020248",
            proxies,
        ),
        ("arXiv", "https://arxiv.org/pdf/2001.00001.pdf", proxies),
        ("Google Scholar (无代理)", "https://scholar.google.com", None),
        ("Sci-Hub", "https://sci-hub.se", proxies),
    ]

    for name, url, test_proxies in tests:
        print(f"\n[{name}]")
        print(f"URL: {url}")
        print(f"代理: {'是' if test_proxies else '否'}")

        try:
            start = time.time()
            response = requests.get(
                url, headers=headers, proxies=test_proxies, timeout=15
            )
            elapsed = time.time() - start

            print(f"✅ 成功 (状态码: {response.status_code}, 耗时: {elapsed:.2f}s)")

            if len(response.text) < 500:
                print(f"响应: {response.text[:200]}")

        except requests.exceptions.Timeout:
            print(f"❌ 超时")
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络错误: {e}")
        except Exception as e:
            print(f"❌ 其他错误: {e}")

        time.sleep(1)

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    test_proxy_and_apis()
