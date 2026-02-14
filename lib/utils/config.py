"""配置管理模块"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import yaml


class Config:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self._config: Dict[str, Any] = {}
        self._config_path = Path(config_path) if config_path else None
        self._load_defaults()

        if self._config_path and self._config_path.exists():
            self._load_from_file()

    def _load_defaults(self) -> None:
        """加载默认配置"""
        self._config = {
            "proxy": {
                "overseas": {
                    "http": "http://127.0.0.1:7897",
                    "https": "http://127.0.0.1:7897",
                },
                "china_network": None,
            },
            "download": {
                "output_dir": "ris_downloads",
                "max_workers": 3,
                "max_retries": 2,
                "timeout": 30,
                "download_timeout": 60,
                "validate_pdf": True,
                "deduplicate": True,
                "show_progress": True,
            },
            "sources": {
                "priority": [
                    "Unpaywall",
                    "Sci-Hub",
                    "Semantic Scholar",
                    "arXiv",
                    "CORE",
                    "Open Access Button",
                    "Europe PMC",
                    "PubMed",
                    "Paperity",
                    "Google Scholar",
                    "ResearchGate",
                ],
                "Unpaywall": {"enabled": True, "email": "your@email.com"},
                "Sci-Hub": {
                    "enabled": True,
                    "domains": [
                        "https://www.sci-hub.ren",
                        "https://sci-hub.hk",
                        "https://sci-hub.la",
                        "https://sci-hub.cat",
                        "https://sci-hub.se",
                        "https://sci-hub.st",
                        "https://sci-hub.ru",
                        "https://sci-hub.wf",
                        "https://sci-hub.yt",
                        "https://sci-hub.do",
                        "https://sci-hub.mksa.top",
                    ],
                },
                "Semantic Scholar": {"enabled": True, "timeout": 15},
                "CORE": {"enabled": True},
                "arXiv": {"enabled": True},
                "Open Access Button": {"enabled": True, "email": "your@email.com"},
                "Europe PMC": {"enabled": True},
                "PubMed": {"enabled": True},
                "Paperity": {"enabled": True},
                "Google Scholar": {"enabled": True, "timeout": 20},
                "ResearchGate": {"enabled": True, "timeout": 20},
            },
            "report": {
                "generate_html": True,
                "generate_text_log": True,
                "realtime_update": False,
                "update_interval": 5,
            },
            "logging": {
                "level": "INFO",
                "file": "ris_downloads/downloader.log",
                "console": True,
            },
        }

    def _load_from_file(self) -> None:
        """从文件加载配置"""
        if not self._config_path:
            return
        try:
            with open(str(self._config_path), "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    self._merge_config(self._config, file_config)
        except (yaml.YAMLError, IOError) as e:
            raise RuntimeError(f"加载配置文件失败: {e}")

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """递归合并配置"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点分隔的键名"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    def get_proxy_config(
        self, use_china_network: bool = False
    ) -> Optional[Dict[str, str]]:
        """获取代理配置"""
        if use_china_network:
            return None
        return self.get("proxy.overseas")

    def get_source_config(self, source_name: str) -> Dict[str, Any]:
        """获取特定下载源的配置"""
        return self.get(f"sources.{source_name}", {})

    def get_enabled_sources(self) -> List[str]:
        """获取启用的下载源列表（按优先级排序）"""
        priority = self.get("sources.priority", [])
        enabled = []
        for source in priority:
            source_config = self.get_source_config(source)
            if source_config.get("enabled", True):
                enabled.append(source)
        return enabled

    def get_scihub_domains(self) -> List[str]:
        """获取 Sci-Hub 域名列表"""
        return self.get("sources.Sci-Hub.domains", [])

    def get_output_dir(self) -> str:
        """获取输出目录"""
        return self.get("download.output_dir", "ris_downloads")

    def get_max_workers(self) -> int:
        """获取最大并发数"""
        return self.get("download.max_workers", 3)

    def get_max_retries(self) -> int:
        """获取最大重试次数"""
        return self.get("download.max_retries", 2)

    def get_timeout(self) -> int:
        """获取请求超时时间"""
        return self.get("download.timeout", 30)

    def get_download_timeout(self) -> int:
        """获取下载超时时间"""
        return self.get("download.download_timeout", 60)

    def get_unpaywall_email(self) -> str:
        """获取 Unpaywall 邮箱"""
        return self.get("sources.Unpaywall.email", "your@email.com")

    @property
    def config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config.copy()
