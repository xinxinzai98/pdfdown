#!/usr/bin/env python3
"""
快速集成示例 - 将 PDF 验证和去重功能集成到下载器
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def add_pdf_validation(downloader):
    """为下载器添加 PDF 验证功能"""

    def validate_pdf(filepath):
        """验证 PDF 是否有效"""
        if not os.path.exists(filepath):
            return False, "文件不存在"

        if os.path.getsize(filepath) < 100:
            return False, "文件过小"

        try:
            # 检查文件头
            with open(filepath, "rb") as f:
                header = f.read(4)
                if header != b"%PDF":
                    return False, "文件头无效"

                # 检查文件尾
                f.seek(-1024, 2)
                tail = f.read()
                if b"%EOF" not in tail:
                    return False, "文件尾无效"

            # 可选: 使用 PyPDF2 进一步验证
            try:
                import PyPDF2

                with open(filepath, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    if len(reader.pages) == 0:
                        return False, "PDF 无页面"
            except ImportError:
                pass  # PyPDF2 未安装

            return True, "有效"
        except Exception as e:
            return False, str(e)

    # 绑定到下载器
    downloader._validate_pdf = validate_pdf
    return downloader


def add_deduplication(downloader):
    """为下载器添加去重功能"""

    def is_already_downloaded(doi):
        """检查 DOI 是否已下载"""
        safe_doi = doi.replace("/", "_").replace(".", "_")

        for filename in os.listdir(downloader.output_dir):
            if safe_doi in filename and filename.endswith(".pdf"):
                filepath = os.path.join(downloader.output_dir, filename)
                valid, _ = downloader._validate_pdf(filepath)
                if valid:
                    return True, filepath

        return False, None

    # 绑定到下载器
    downloader._is_already_downloaded = is_already_downloaded
    return downloader


def add_progress_bar(downloader):
    """为下载器添加进度条功能"""

    def download_with_progress(url, doi, source, proxies=None):
        """带进度条的下载"""
        try:
            import tqdm

            response = downloader.session.get(
                url, stream=True, proxies=proxies, timeout=30
            )

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()

                if "pdf" in content_type or url.lower().endswith(".pdf"):
                    safe_doi = doi.replace("/", "_").replace(".", "_")
                    filename = f"{source}_{safe_doi}.pdf"
                    filepath = os.path.join(downloader.output_dir, filename)

                    # 获取文件大小
                    total_size = int(response.headers.get("content-length", 0))

                    # 带进度条的下载
                    with open(filepath, "wb") as f:
                        with tqdm.tqdm(
                            total=total_size,
                            unit="B",
                            unit_scale=True,
                            desc=filename[:30],
                            leave=False,
                        ) as pbar:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    pbar.update(len(chunk))

                    file_size = os.path.getsize(filepath)

                    # 验证 PDF
                    valid, msg = downloader._validate_pdf(filepath)
                    if not valid:
                        os.remove(filepath)
                        print(f"    ❌ PDF 无效: {msg}")
                        return {"success": False, "error": f"无效 PDF: {msg}"}

                    print(f"    ✅ {filename} ({file_size:,} bytes) - 已验证")

                    return {"success": True, "file": filepath, "size": file_size}

            return {"success": False}
        except ImportError:
            # tqdm 未安装,使用原方法
            return downloader._download_and_save(url, doi, source, proxies)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # 绑定到下载器
    downloader._download_and_save = download_with_progress
    return downloader


def enhance_downloader(downloader):
    """一键增强下载器"""
    downloader = add_pdf_validation(downloader)
    downloader = add_deduplication(downloader)
    downloader = add_progress_bar(downloader)

    # 打印增强信息
    print("=" * 70)
    print("🚀 下载器已增强")
    print("=" * 70)
    print("✅ PDF 验证")
    print("✅ 文件去重")
    print("✅ 下载进度条")
    print("=" * 70)

    return downloader


if __name__ == "__main__":
    from multi_source_ris_downloader_v3 import MultiSourceDownloader

    # 创建基础下载器
    downloader = MultiSourceDownloader(max_workers=1, max_retries=1)

    # 增强下载器
    downloader = enhance_downloader(downloader)

    # 测试下载
    print("\n🧪 测试下载 (带增强功能)")
    print("=" * 70)

    test_doi = "10.3390/pr8020248"

    # 检查是否已下载
    exists, filepath = downloader._is_already_downloaded(test_doi)
    if exists:
        print(f"✅ {test_doi} 已下载: {filepath}")
        print("跳过下载...")
    else:
        print(f"📥 {test_doi} 未下载,开始下载...")
        success = downloader.download_doi(test_doi, index=1, total=1)

        if success:
            print("✅ 下载成功!")
        else:
            print("❌ 下载失败")
