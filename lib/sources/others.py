"""其他下载源"""

import re
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from .base import BaseSource


class SemanticScholarSource(BaseSource):
    """Semantic Scholar 下载源"""

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        try:
            url = f"https://api.semanticscholar.org/v1/paper/DOI:{doi}"
            response = self._try_request(url, timeout=15, proxies=proxies)

            if not response or response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code if response else 'None'}",
                }

            data = response.json()

            oa_pdf = data.get("openAccessPdf")
            if oa_pdf:
                pdf_url = oa_pdf.get("url")
                if pdf_url:
                    return {
                        "success": True,
                        "pdf_url": pdf_url,
                        "source": "Semantic_Scholar",
                    }

            for source in data.get("sources", []):
                url = source.get("url")
                if url and "pdf" in url.lower():
                    return {
                        "success": True,
                        "pdf_url": url,
                        "source": "Semantic_Scholar",
                    }

            return {"success": False, "error": "无 PDF 链接"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class ArxivSource(BaseSource):
    """arXiv 下载源"""

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        if "arxiv" not in doi.lower():
            return {"success": False, "error": "非 arXiv 论文"}

        arxiv_pattern = re.compile(r"(?:10\.\d+/)?arxiv\.?/?(\d+\.\d+)", re.IGNORECASE)
        match = arxiv_pattern.search(doi)

        if match:
            arxiv_id = match.group(1)
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            return {"success": True, "pdf_url": pdf_url, "source": "arXiv"}

        return {"success": False, "error": "无法解析 arXiv ID"}


class CoreSource(BaseSource):
    """CORE 下载源"""

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        try:
            url = f"https://core.ac.uk/search?q={quote(doi)}"
            response = self._try_request(url, timeout=15, proxies=proxies)

            if not response or response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code if response else 'None'}",
                }

            pdf_pattern = re.compile(
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(response.text)

            for pdf_url in pdf_links[:3]:
                if pdf_url.startswith("https://core.ac.uk/download"):
                    return {"success": True, "pdf_url": pdf_url, "source": "CORE"}

            return {"success": False, "error": "无 PDF 链接"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class OpenAccessButtonSource(BaseSource):
    """Open Access Button 下载源"""

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        try:
            email = self.config.get("email", "your@email.com")
            url = f"https://api.openaccessbutton.org/v2/{doi}?email={email}"
            response = self._try_request(url, timeout=10, proxies=proxies)

            if not response or response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code if response else 'None'}",
                }

            data = response.json()
            if data.get("status") == "success" and data.get("file_type") == "pdf":
                pdf_url = data.get("file_url")
                if pdf_url:
                    return {"success": True, "pdf_url": pdf_url, "source": "OpenAccess"}

            return {"success": False, "error": "无 PDF 链接"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class EuropePMCSource(BaseSource):
    """Europe PMC 下载源"""

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        try:
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{doi}&resulttype=core"
            response = self._try_request(url, timeout=10, proxies=proxies)

            if not response or response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code if response else 'None'}",
                }

            pdf_pattern = re.compile(r'openAccess="Y"[^>]*>([^<]+)<', re.IGNORECASE)
            matches = pdf_pattern.findall(response.text)

            for pdf_url in matches[:3]:
                if pdf_url and "pdf" in pdf_url.lower():
                    return {"success": True, "pdf_url": pdf_url, "source": "EuropePMC"}

            return {"success": False, "error": "无 PDF 链接"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class PubMedSource(BaseSource):
    """PubMed 下载源"""

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        try:
            url = f"https://pubmed.ncbi.nlm.nih.gov/?term={quote(doi)}"
            response = self._try_request(url, timeout=10, proxies=proxies)

            if not response or response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code if response else 'None'}",
                }

            pdf_pattern = re.compile(
                r'href=["\']([^"\']*\/pdf\/[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(response.text)

            for pdf_url in pdf_links[:2]:
                if "pdf" in pdf_url.lower():
                    return {"success": True, "pdf_url": pdf_url, "source": "PubMed"}

            return {"success": False, "error": "无 PDF 链接"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class PaperitySource(BaseSource):
    """Paperity 下载源"""

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        try:
            url = f"https://paperity.org/search/?q={quote(doi)}"
            response = self._try_request(url, timeout=10, proxies=proxies)

            if not response or response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code if response else 'None'}",
                }

            pdf_pattern = re.compile(
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(response.text)

            for pdf_url in pdf_links[:3]:
                if pdf_url and "download" in pdf_url.lower():
                    return {"success": True, "pdf_url": pdf_url, "source": "Paperity"}

            return {"success": False, "error": "无 PDF 链接"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class GoogleScholarSource(BaseSource):
    """Google Scholar 下载源"""

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        try:
            url = f"https://scholar.google.com/scholar?q={quote(doi)}"
            response = self.session.get(url, timeout=20, proxies=None)

            if not response or response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code if response else 'None'}",
                }

            pdf_pattern = re.compile(
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(response.text)

            for pdf_url in pdf_links[:2]:
                if pdf_url and pdf_url.startswith("http"):
                    return {
                        "success": True,
                        "pdf_url": pdf_url,
                        "source": "GoogleScholar",
                    }

            return {"success": False, "error": "无 PDF 链接"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class ResearchGateSource(BaseSource):
    """ResearchGate 下载源"""

    def download(
        self, doi: str, proxies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        try:
            url = f"https://www.researchgate.net/search?q={quote(doi)}"
            response = self.session.get(url, timeout=20, proxies=None)

            if not response or response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code if response else 'None'}",
                }

            pdf_pattern = re.compile(
                r'href=["\']([^"\']*\/fullText\/pdf\/[^"\']*)["\']', re.IGNORECASE
            )
            pdf_links = pdf_pattern.findall(response.text)

            for pdf_url in pdf_links[:2]:
                if pdf_url:
                    return {
                        "success": True,
                        "pdf_url": pdf_url,
                        "source": "ResearchGate",
                    }

            return {"success": False, "error": "无 PDF 链接"}

        except Exception as e:
            return {"success": False, "error": str(e)}
