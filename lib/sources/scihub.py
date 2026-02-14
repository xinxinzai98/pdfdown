"""Sci-Hub 下载源 (改进版)"""

import os
import re
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseSource

logger = logging.getLogger(__name__)


class ScihubSource(BaseSource):
    """Sci-Hub 下载源 (改进版，支持代理)"""

    def __init__(self, session: requests.Session, config: Dict[str, Any]):
        super().__init__(session, config)
        self.domains: List[str] = config.get(
            "domains",
            [
                "https://sci-hub.se",
                "https://sci-hub.st",
                "https://sci-hub.ru",
                "https://sci-hub.wf",
                "https://sci-hub.do",
            ],
        )
        self.proxy = self._get_proxy(config)
        self.available_domains = self._get_available_domains()
        self.current_domain = (
            self.available_domains[0] if self.available_domains else self.domains[0]
        )
        if self.proxy:
            logger.info(f"Sci-Hub 使用代理: {list(self.proxy.values())[0]}")

    def _get_proxy(self, config: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """获取代理配置，优先级：配置 > 环境变量 > 默认本地"""
        proxy_config = config.get("proxy")

        if proxy_config:
            if proxy_config.startswith("socks"):
                return {"http": proxy_config, "https": proxy_config}
            elif proxy_config.startswith("http"):
                return {"http": proxy_config, "https": proxy_config}

        http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        all_proxy = os.environ.get("ALL_PROXY") or os.environ.get("all_proxy")

        if all_proxy:
            return {"http": all_proxy, "https": all_proxy}
        if http_proxy or https_proxy:
            return {
                "http": http_proxy or https_proxy,
                "https": https_proxy or http_proxy,
            }

        default_socks = "socks5://127.0.0.1:7897"
        default_http = "http://127.0.0.1:7897"

        return {"http": default_http, "https": default_http}

    def _get_available_domains(self) -> List[str]:
        """从镜像列表网站获取可用的 Sci-Hub 域名"""
        available = []
        try:
            res = requests.get(
                "http://tool.yovisun.com/scihub/",
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                proxies=self.proxy,
            )
            if res.status_code == 200:
                soup = BeautifulSoup(res.content, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "sci-hub." in href and href.startswith("http"):
                        available.append(href.rstrip("/"))
        except Exception as e:
            logger.debug(f"获取Sci-Hub镜像列表失败: {e}")

        if not available:
            available = self.domains.copy()

        logger.info(f"可用的Sci-Hub域名: {available[:3]}...")
        return available

    def _switch_domain(self) -> bool:
        """切换到下一个可用域名"""
        if len(self.available_domains) <= 1:
            return False
        self.available_domains.pop(0)
        if self.available_domains:
            self.current_domain = self.available_domains[0]
            logger.info(f"切换到域名: {self.current_domain}")
            return True
        return False

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """从 Sci-Hub 下载 (始终使用代理)"""
        effective_proxies = self.proxy or proxies

        for attempt in range(min(3, len(self.available_domains))):
            result = self._try_download(self.current_domain, doi, effective_proxies)
            if result.get("success"):
                return result

            if result.get("need_switch"):
                if not self._switch_domain():
                    break
            else:
                break

        return {"success": False, "error": "所有 Sci-Hub 域名均失败"}

    def _try_download(
        self, domain: str, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """尝试从特定域名下载"""
        try:
            url = f"{domain}/{doi}"
            logger.info(f"Sci-Hub 尝试: {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }

            response = requests.get(
                url,
                timeout=20,
                headers=headers,
                proxies=proxies,
                allow_redirects=True,
                verify=False,
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "need_switch": True,
                }

            content_type = response.headers.get("Content-Type", "").lower()

            if "pdf" in content_type:
                return {
                    "success": True,
                    "pdf_url": url,
                    "direct_response": True,
                    "source": "Sci-Hub",
                }

            pdf_url = self._extract_pdf_url(response.text, response.url)
            if pdf_url:
                pdf_url = self._normalize_url(pdf_url, domain)
                logger.info(f"Sci-Hub 找到PDF: {pdf_url[:80]}...")
                return {"success": True, "pdf_url": pdf_url, "source": "Sci-Hub"}

            if (
                "captcha" in response.text.lower()
                or "cloudflare" in response.text.lower()
            ):
                return {
                    "success": False,
                    "error": "验证码或Cloudflare拦截",
                    "need_switch": True,
                }

            return {"success": False, "error": "未找到 PDF 链接"}

        except requests.exceptions.Timeout:
            return {"success": False, "error": "请求超时", "need_switch": True}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "连接失败", "need_switch": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_pdf_url(self, html: str, base_url: str) -> Optional[str]:
        """从 HTML 中提取 PDF URL (支持新版和旧版 Sci-Hub)"""
        try:
            soup = BeautifulSoup(html, "html.parser")

            embed = soup.find("embed")
            if embed and embed.get("src"):
                src = embed.get("src")
                if ".pdf" in str(src) or src.startswith("http"):
                    return str(src)

            iframe = soup.find("iframe")
            if iframe and iframe.get("src"):
                src = iframe.get("src")
                if ".pdf" in str(src) or src.startswith("http"):
                    return str(src)

            pdf_pattern = re.compile(
                r'(?:src|href)\s*=\s*["\']([^"\'>]*\.pdf[^"\'>]*)["\']', re.IGNORECASE
            )
            matches = pdf_pattern.findall(html)
            for match in matches:
                if match.startswith("http") or match.startswith("//"):
                    return match

            button_pattern = re.compile(
                r'<button[^>]*onclick\s*=\s*["\'].*?location\.href\s*=\s*["\']([^"\'>]+)["\']',
                re.IGNORECASE,
            )
            button_matches = button_pattern.findall(html)
            for match in button_matches:
                if ".pdf" in match or match.startswith("http"):
                    return match

        except Exception as e:
            logger.debug(f"PDF提取失败: {e}")

        return None

    def _normalize_url(self, url: str, base_domain: str) -> str:
        """规范化 URL"""
        if url.startswith("//"):
            return "https:" + url
        elif url.startswith("/"):
            return base_domain + url
        elif not url.startswith("http"):
            return f"{base_domain}/{url}"
        return url
