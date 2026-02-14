"""下载源基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import requests


class BaseSource(ABC):
    """下载源基类"""

    def __init__(self, session: requests.Session, config: Dict[str, Any]):
        self.session = session
        self.config = config
        self.name = self.__class__.__name__.replace("Source", "")

    @abstractmethod
    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """下载方法

        Args:
            doi: DOI
            proxies: 代理配置

        Returns:
            dict: {"success": bool, "file": str, "size": int, "error": str}
        """
        pass

    @property
    def enabled(self) -> bool:
        """是否启用"""
        return self.config.get("enabled", True)

    def _try_request(
        self,
        url: str,
        timeout: int = 10,
        proxies: Optional[Dict[str, str]] = None,
        allow_redirects: bool = True,
    ) -> Optional[requests.Response]:
        """尝试请求，失败时重试无代理"""
        try:
            return self.session.get(
                url,
                timeout=timeout,
                proxies=proxies,
                allow_redirects=allow_redirects,
            )
        except (
            requests.exceptions.ProxyError,
            requests.exceptions.Timeout,
            requests.exceptions.SSLError,
        ):
            if proxies is not None:
                try:
                    return self.session.get(
                        url,
                        timeout=timeout,
                        proxies=None,
                        allow_redirects=allow_redirects,
                    )
                except Exception:
                    pass
        except Exception:
            pass
        return None
