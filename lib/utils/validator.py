"""PDF 验证工具模块"""

import os
from typing import Tuple


def validate_pdf(filepath: str) -> Tuple[bool, str]:
    """验证 PDF 文件是否有效

    Args:
        filepath: PDF 文件路径

    Returns:
        tuple: (是否有效, 消息)
    """
    if not os.path.exists(filepath):
        return False, "文件不存在"

    if os.path.getsize(filepath) < 100:
        return False, "文件过小"

    try:
        with open(filepath, "rb") as f:
            header = f.read(4)
            if header != b"%PDF":
                return False, "文件头无效 (不是 PDF)"

            file_size = os.path.getsize(filepath)
            seek_pos = max(0, file_size - 1024)
            f.seek(seek_pos)
            tail = f.read()
            if b"%EOF" not in tail:
                return False, "文件尾无效 (未完成)"

        try:
            import PyPDF2

            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if len(reader.pages) == 0:
                    return False, "PDF 无页面"
        except ImportError:
            pass
        except Exception:
            pass

        return True, "PDF 有效"

    except Exception as e:
        return False, f"验证失败: {e}"


def clean_invalid_pdfs(directory: str) -> list:
    """清理目录中无效的 PDF 文件

    Args:
        directory: 目录路径

    Returns:
        list: 删除的文件列表
    """
    deleted_files = []

    if not os.path.exists(directory):
        return deleted_files

    for filename in os.listdir(directory):
        if not filename.lower().endswith(".pdf"):
            continue

        filepath = os.path.join(directory, filename)
        valid, msg = validate_pdf(filepath)

        if not valid:
            os.remove(filepath)
            deleted_files.append(filename)

    return deleted_files


def scan_directory(directory: str) -> dict:
    """扫描目录中的所有 PDF 文件

    Args:
        directory: 目录路径

    Returns:
        dict: 统计信息
    """
    stats = {"total": 0, "valid": 0, "invalid": 0, "files": []}

    if not os.path.exists(directory):
        return stats

    for filename in os.listdir(directory):
        if not filename.lower().endswith(".pdf"):
            continue

        filepath = os.path.join(directory, filename)
        file_size = os.path.getsize(filepath)
        valid, msg = validate_pdf(filepath)

        stats["total"] += 1
        if valid:
            stats["valid"] += 1
        else:
            stats["invalid"] += 1

        stats["files"].append(
            {
                "filename": filename,
                "filepath": filepath,
                "size": file_size,
                "valid": valid,
                "message": msg,
            }
        )

    return stats
