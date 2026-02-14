"""
PaperDownloader - 学术文献批量下载工具库

模块化重构版本 v4.0
"""

from .core.downloader import MultiSourceDownloader
from .utils.config import Config
from .utils.logger import setup_logger

__version__ = "4.0.0"
__all__ = ["MultiSourceDownloader", "Config", "setup_logger"]
