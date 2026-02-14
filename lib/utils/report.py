"""HTML 报告生成器模块"""

import os
from datetime import datetime
from html import escape
from typing import Any, Dict, List, Optional


class HTMLReportGenerator:
    """HTML 报告生成器"""

    def __init__(self, output_dir: str, max_workers: int = 3, max_retries: int = 2):
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.report_data: Dict[str, Any] = {
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": None,
            "total": 0,
            "success": 0,
            "failed": 0,
            "items": [],
        }

    def add_item(
        self,
        index: int,
        doi: str,
        status: str,
        attempts: List[Dict[str, Any]],
        final_source: Optional[str] = None,
        file: Optional[str] = None,
        size: int = 0,
    ) -> None:
        """添加下载项"""
        self.report_data["items"].append(
            {
                "index": index,
                "doi": doi,
                "status": status,
                "attempts": attempts,
                "final_source": final_source,
                "file": file,
                "size": size,
            }
        )

    def update_summary(self, total: int, success: int, failed: int) -> None:
        """更新汇总信息"""
        self.report_data["total"] = total
        self.report_data["success"] = success
        self.report_data["failed"] = failed
        self.report_data["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate(self) -> str:
        """生成 HTML 报告"""
        html = self._build_html()
        filepath = os.path.join(self.output_dir, "download_report.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return filepath

    def _escape(self, text: Any) -> str:
        """安全转义 HTML"""
        if text is None:
            return ""
        return escape(str(text))

    def _get_official_links(self, doi: str) -> str:
        """生成官方下载链接"""
        links = []
        doi_encoded = doi.replace("/", "%2F")

        links.append(
            f'<a href="https://doi.org/{doi}" target="_blank" class="official-link doi">🔗 DOI 官方</a>'
        )
        links.append(
            f'<a href="https://scholar.google.com/scholar?q={doi_encoded}" target="_blank" class="official-link scholar">🎓 Google Scholar</a>'
        )
        links.append(
            f'<a href="https://www.researchgate.net/search?q={doi_encoded}" target="_blank" class="official-link rg">📚 ResearchGate</a>'
        )
        links.append(
            f'<a href="https://www.ncbi.nlm.nih.gov/pmc/?term={doi_encoded}" target="_blank" class="official-link pmc">🧬 PubMed Central</a>'
        )
        links.append(
            f'<a href="https://sci-hub.se/{doi}" target="_blank" class="official-link scihub">⚠️ Sci-Hub</a>'
        )

        return " | ".join(links)

    def _build_html(self) -> str:
        """构建 HTML 内容"""
        data = self.report_data
        success_rate = data["success"] / data["total"] * 100 if data["total"] > 0 else 0

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文献下载报告 - {self._escape(data["start_time"])}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .subtitle {{ font-size: 1.1em; opacity: 0.9; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; color: #667eea; }}
        .stat-label {{ color: #6c757d; font-size: 0.9em; margin-top: 5px; }}
        .success .stat-value {{ color: #28a745; }}
        .failed .stat-value {{ color: #dc3545; }}
        .progress-bar {{
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            margin: 20px 30px;
            overflow: hidden;
            display: flex;
        }}
        .progress-fill {{
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
        .progress-fill.success {{ background: linear-gradient(90deg, #28a745, #34d399); }}
        .progress-fill.failed {{ background: linear-gradient(90deg, #dc3545, #f87171); }}
        .items {{ padding: 30px; }}
        .items h2 {{ margin-bottom: 20px; color: #333; }}
        .item {{
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
        }}
        .item.success {{ border-left: 5px solid #28a745; }}
        .item.failed {{ border-left: 5px solid #dc3545; }}
        .item-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .item-doi {{ font-weight: bold; font-size: 1.1em; color: #333; }}
        .item-status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .item-status.success {{ background: #d4edda; color: #155724; }}
        .item-status.failed {{ background: #f8d7da; color: #721c24; }}
        .item-details {{ font-size: 0.9em; color: #6c757d; line-height: 1.6; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            margin-right: 5px;
        }}
        .badge.source {{ background: #007bff; color: white; }}
        .badge.retry {{ background: #ffc107; color: #333; }}
        .attempt-log {{
            margin-top: 10px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            font-size: 0.85em;
        }}
        .attempt {{ margin: 5px 0; padding: 5px; background: white; border-radius: 3px; }}
        .attempt.success {{ border-left: 3px solid #28a745; }}
        .attempt.failed {{ border-left: 3px solid #dc3545; }}
        .official-links {{
            margin-top: 15px;
            padding: 12px;
            background: linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%);
            border-radius: 8px;
            border: 1px solid #ffcdd2;
        }}
        .official-links-title {{
            font-weight: bold;
            color: #c62828;
            margin-bottom: 8px;
            font-size: 0.95em;
        }}
        .official-link {{
            display: inline-block;
            padding: 4px 10px;
            margin: 3px;
            background: white;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.85em;
            border: 1px solid #ddd;
            transition: all 0.2s;
        }}
        .official-link:hover {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}
        .official-link.doi {{ color: #1565c0; }}
        .official-link.scholar {{ color: #f9a825; }}
        .official-link.rg {{ color: #00bcd4; }}
        .official-link.pmc {{ color: #388e3c; }}
        .official-link.scihub {{ color: #e53935; }}
        .footer {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 文献下载报告</h1>
            <p class="subtitle">v4.0 模块化版本 - {self._escape(data["start_time"])}</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{data["total"]}</div>
                <div class="stat-label">总文献数</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">{data["success"]}</div>
                <div class="stat-label">成功下载</div>
            </div>
            <div class="stat-card failed">
                <div class="stat-value">{data["failed"]}</div>
                <div class="stat-label">下载失败</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{success_rate:.1f}%</div>
                <div class="stat-label">成功率</div>
            </div>
        </div>

        <div class="progress-bar">
            <div class="progress-fill success" style="width: {success_rate}%">
                {data["success"]} 成功
            </div>
            <div class="progress-fill failed" style="width: {100 - success_rate}%">
                {data["failed"]} 失败
            </div>
        </div>

        <div class="items">
            <h2>📋 下载详情</h2>
"""

        for item in data["items"]:
            status_class = item.get("status", "failed")
            status_text = "✅ 成功" if item["status"] == "success" else "❌ 失败"

            html += f"""
            <div class="item {status_class}">
                <div class="item-header">
                    <span class="item-doi">[{self._escape(item["index"])}] {self._escape(item["doi"])}</span>
                    <span class="item-status {status_class}">{status_text}</span>
                </div>
                <div class="item-details">
"""

            if item["status"] == "success":
                html += f"""
                    <p><strong>下载来源:</strong> <span class="badge source">{self._escape(item["final_source"])}</span></p>
                    <p><strong>文件路径:</strong> {self._escape(item["file"])}</p>
                    <p><strong>文件大小:</strong> {item["size"]:,} bytes ({item["size"] / 1024:.1f} KB)</p>
"""

            if item["attempts"]:
                html += """
                    <div class="attempt-log">
                        <strong>尝试记录:</strong>
"""
                for attempt in item["attempts"]:
                    attempt_status = "✅" if attempt["status"] == "success" else "❌"
                    html += f"""
                        <div class="attempt {attempt["status"]}">
                            {attempt_status} <span class="badge source">{self._escape(attempt["source"])}</span>
                            <span class="badge retry">重试 #{attempt["retry"]}</span>
                            {self._escape(attempt["status"])}
                        </div>
"""
                html += """
                    </div>
"""

            if item["status"] != "success":
                html += f"""
                    <div class="official-links">
                        <div class="official-links-title">📥 官方下载通道 (手动下载)</div>
                        <div>{self._get_official_links(item["doi"])}</div>
                    </div>
"""

            html += """
                </div>
            </div>
"""

        html += f"""
        </div>

        <div class="footer">
            <p>📅 生成时间: {self._escape(data["end_time"])}</p>
            <p>🚀 多源并发下载 | 最大重试次数: {self.max_retries} | 并发数: {self.max_workers}</p>
        </div>
    </div>
</body>
</html>
"""

        return html
