#!/usr/bin/env python3
"""
浏览器版 RIS 文件批量下载器 - 使用 Playwright 模拟真实浏览器下载

优势：
1. 绕过反爬虫检测
2. 支持 JavaScript 渲染的页面
3. 可以手动通过验证（交互模式）
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.sources.multi_channel_browser import MultiChannelBrowserDownloader
from lib.utils.report import HTMLReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_ris_file(ris_path: str) -> List[Dict[str, str]]:
    """解析 RIS 文件，提取 DOI 和元数据"""
    papers = []
    current_entry = {}

    with open(ris_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith("TY  -"):
                if current_entry and current_entry.get("doi"):
                    papers.append(current_entry)
                current_entry = {}
            elif line.startswith("DO  -"):
                current_entry["doi"] = line[5:].strip()
            elif line.startswith("TI  -"):
                current_entry["title"] = line[5:].strip()
            elif line.startswith("AU  -"):
                if "authors" not in current_entry:
                    current_entry["authors"] = []
                current_entry["authors"].append(line[5:].strip())
            elif line.startswith("PY  -"):
                current_entry["year"] = line[5:].strip()[:4]
            elif line.startswith("T2  -"):
                current_entry["journal"] = line[5:].strip()

        if current_entry and current_entry.get("doi"):
            papers.append(current_entry)

    return papers


async def download_papers(
    papers: List[Dict[str, str]],
    output_dir: str,
    sources: List[str],
    proxy: Optional[str],
    interactive: bool,
    wait_time: int,
    max_workers: int = 3,
) -> Dict:
    """批量下载论文"""

    downloader = MultiChannelBrowserDownloader(
        proxy=proxy, headless=not interactive, download_dir=output_dir
    )

    results = {"total": len(papers), "success": 0, "failed": 0, "items": []}

    try:
        for i, paper in enumerate(papers, 1):
            doi = paper.get("doi", "")
            title = paper.get("title", "Unknown")

            logger.info(f"\n{'=' * 60}")
            logger.info(f"[{i}/{len(papers)}] 处理: {doi}")
            logger.info(f"  标题: {title[:60]}...")
            logger.info(f"{'=' * 60}")

            result = await downloader.download(
                doi, sources=sources, interactive=interactive, wait_time=wait_time
            )

            item = {
                "index": i,
                "doi": doi,
                "title": title,
                "status": "success" if result["success"] else "failed",
                "file": result.get("file"),
                "source": result.get("source"),
                "attempts": result.get("attempts", []),
            }

            results["items"].append(item)

            if result["success"]:
                results["success"] += 1
                logger.info(f"✅ [{i}/{len(papers)}] 下载成功: {result['file']}")
            else:
                results["failed"] += 1
                logger.warning(f"❌ [{i}/{len(papers)}] 下载失败")

            # 避免请求过快
            await asyncio.sleep(2)

    finally:
        await downloader.close()

    return results


def generate_report(results: Dict, output_dir: str, start_time: str, end_time: str):
    """生成下载报告"""
    report = HTMLReportGenerator(output_dir, 3, 0)

    for item in results["items"]:
        attempts = [
            {
                "source": a.get("source", "unknown"),
                "retry": 1,
                "status": "success" if a.get("success") else "failed",
            }
            for a in item.get("attempts", [])
        ]

        report.add_item(
            index=item["index"],
            doi=item["doi"],
            status=item["status"],
            attempts=attempts,
            final_source=item.get("source"),
            file=item.get("file"),
            size=0,
        )

    report.update_summary(
        total=results["total"], success=results["success"], failed=results["failed"]
    )

    html_file = report.generate()

    # 生成文本总结
    summary_file = os.path.join(output_dir, "download_summary.txt")
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"RIS 文件浏览器批量下载总结\n")
        f.write(f"时间: {end_time}\n")
        f.write(f"总计: {results['total']} 篇\n")
        f.write(f"成功: {results['success']} 篇\n")
        f.write(f"失败: {results['failed']} 篇\n")
        success_rate = (
            results["success"] / results["total"] * 100 if results["total"] > 0 else 0
        )
        f.write(f"成功率: {success_rate:.1f}%\n\n")

        f.write("成功列表:\n")
        for item in results["items"]:
            if item["status"] == "success":
                f.write(f"  {item['doi']}\n")
                f.write(f"    来源: {item.get('source', 'unknown')}\n")
                f.write(f"    文件: {item.get('file', 'N/A')}\n\n")

        f.write("\n失败列表:\n")
        for item in results["items"]:
            if item["status"] == "failed":
                f.write(f"  {item['doi']}\n")

    return html_file, summary_file


async def main():
    parser = argparse.ArgumentParser(description="浏览器版 RIS 文件批量下载器")
    parser.add_argument("ris_file", help="RIS 文件路径")
    parser.add_argument(
        "--output", "-o", default="./browser_downloads", help="输出目录"
    )
    parser.add_argument(
        "--sources",
        "-s",
        nargs="+",
        default=["unpaywall", "semantic_scholar", "scihub"],
        help="下载源",
    )
    parser.add_argument("--proxy", help="代理服务器")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="交互模式（显示浏览器）"
    )
    parser.add_argument("--wait", type=int, default=30, help="交互模式等待时间")

    args = parser.parse_args()

    if not os.path.exists(args.ris_file):
        logger.error(f"文件不存在: {args.ris_file}")
        sys.exit(1)

    proxy = args.proxy or os.environ.get("HTTP_PROXY") or "http://127.0.0.1:7897"

    print(f"""
╔════════════════════════════════════════════════════╗
║     浏览器版 RIS 批量下载器 v1.0                   ║
╠════════════════════════════════════════════════════╣
║  RIS 文件: {args.ris_file:<39}║
║  输出目录: {args.output:<39}║
║  下载源: {str(args.sources):<41}║
║  代理: {proxy:<43}║
║  交互模式: {str(args.interactive):<39}║
╚════════════════════════════════════════════════════╝
""")

    start_time = time.strftime("%Y-%m-%d %H:%M:%S")

    # 解析 RIS 文件
    logger.info(f"📖 解析 RIS 文件: {args.ris_file}")
    papers = parse_ris_file(args.ris_file)
    logger.info(f"📋 找到 {len(papers)} 篇文献")

    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)

    # 批量下载
    results = await download_papers(
        papers, args.output, args.sources, proxy, args.interactive, args.wait
    )

    end_time = time.strftime("%Y-%m-%d %H:%M:%S")

    # 生成报告
    html_file, summary_file = generate_report(
        results, args.output, start_time, end_time
    )

    # 打印总结
    print(f"""
╔════════════════════════════════════════════════════╗
║                  📊 下载总结                        ║
╠════════════════════════════════════════════════════╣
║  ✅ 成功: {results["success"]}/{results["total"]} 篇                              ║
║  ❌ 失败: {results["failed"]}/{results["total"]} 篇                              ║
║  📈 成功率: {results["success"] / results["total"] * 100:.1f}%                           ║
╚════════════════════════════════════════════════════╝
""")

    if results["success"] > 0:
        print("✅ 成功列表:")
        for item in results["items"]:
            if item["status"] == "success":
                print(f"   ✓ {item['doi']}")
                print(f"     来源: {item.get('source', 'unknown')}")

    if results["failed"] > 0:
        print("\n❌ 失败列表:")
        for item in results["items"]:
            if item["status"] == "failed":
                print(f"   ✗ {item['doi']}")

    print(f"\n📝 详细日志: {summary_file}")
    print(f"🌐 HTML 报告: {html_file}")


if __name__ == "__main__":
    asyncio.run(main())
