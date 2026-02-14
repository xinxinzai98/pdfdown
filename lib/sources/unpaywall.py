"""Unpaywall 下载源"""

from typing import Any, Dict, Optional

import requests

from .base import BaseSource


class UnpaywallSource(BaseSource):
    """Unpaywall API 下载源"""

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """从 Unpaywall 下载"""
        try:
            email = self.config.get("email", "your@email.com")
            url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}

            data = response.json()
            if not data.get("is_oa"):
                return {"success": False, "error": "非开放获取"}

            pdf_url = data.get("best_oa_location", {}).get("url")
            if not pdf_url:
                return {"success": False, "error": "无 PDF 链接"}

            return {"success": True, "pdf_url": pdf_url, "source": "Unpaywall"}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}
