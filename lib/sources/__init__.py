"""下载源模块"""

from typing import Any, Dict, Type

import requests

from .base import BaseSource
from .others import (
    ArxivSource,
    CoreSource,
    EuropePMCSource,
    GoogleScholarSource,
    OpenAccessButtonSource,
    PaperitySource,
    PubMedSource,
    ResearchGateSource,
    SemanticScholarSource,
)
from .scihub import ScihubSource
from .unpaywall import UnpaywallSource

SOURCE_REGISTRY: Dict[str, Type[BaseSource]] = {
    "Unpaywall": UnpaywallSource,
    "Sci-Hub": ScihubSource,
    "Semantic Scholar": SemanticScholarSource,
    "arXiv": ArxivSource,
    "CORE": CoreSource,
    "Open Access Button": OpenAccessButtonSource,
    "Europe PMC": EuropePMCSource,
    "PubMed": PubMedSource,
    "Paperity": PaperitySource,
    "Google Scholar": GoogleScholarSource,
    "ResearchGate": ResearchGateSource,
}

__all__ = [
    "BaseSource",
    "UnpaywallSource",
    "ScihubSource",
    "SemanticScholarSource",
    "ArxivSource",
    "CoreSource",
    "OpenAccessButtonSource",
    "EuropePMCSource",
    "PubMedSource",
    "PaperitySource",
    "GoogleScholarSource",
    "ResearchGateSource",
    "SOURCE_REGISTRY",
]


def create_source(
    name: str, session: requests.Session, config: Dict[str, Any]
) -> BaseSource:
    """创建下载源实例"""
    source_class = SOURCE_REGISTRY.get(name)
    if not source_class:
        raise ValueError(f"未知的下载源: {name}")
    return source_class(session, config)
