#!/usr/bin/env python3
"""
PDF 文件验证工具
"""

import os
import re


def validate_pdf(filepath):
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
        # 方法1: 检查文件头
        with open(filepath, "rb") as f:
            header = f.read(4)
            if header != b"%PDF":
                return False, "文件头无效 (不是 PDF)"

            # 检查文件尾
            f.seek(-1024, 2)
            tail = f.read()
            if b"%EOF" not in tail:
                return False, "文件尾无效 (未完成)"

        # 方法2: 使用 PyPDF2 验证 (如果安装了)
        try:
            import PyPDF2

            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if len(reader.pages) == 0:
                    return False, "PDF 无页面"
        except ImportError:
            pass  # PyPDF2 未安装,跳过此检查
        except Exception as e:
            return False, f"PDF 解析失败: {e}"

        return True, "PDF 有效"

    except Exception as e:
        return False, f"验证失败: {e}"


def clean_invalid_pdfs(directory):
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
            print(f"❌ 删除无效 PDF: {filename} - {msg}")
            os.remove(filepath)
            deleted_files.append(filename)

    return deleted_files


def scan_directory(directory):
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


if __name__ == "__main__":
    import sys

    directory = sys.argv[1] if len(sys.argv) > 1 else "."

    print("=" * 70)
    print("📄 PDF 文件扫描工具")
    print("=" * 70)
    print(f"目录: {directory}\n")

    stats = scan_directory(directory)

    print(f"📊 统计:")
    print(f"  总数: {stats['total']}")
    print(f"  有效: {stats['valid']}")
    print(f"  无效: {stats['invalid']}\n")

    if stats["invalid"] > 0:
        print("❌ 无效文件:")
        for file_info in stats["files"]:
            if not file_info["valid"]:
                print(f"  - {file_info['filename']} ({file_info['size']:,} bytes)")
                print(f"    原因: {file_info['message']}")

        print("\n💡 提示: 运行以下命令清理无效文件:")
        print(f"  python3 {sys.argv[0]} {directory} --clean")

        if "--clean" in sys.argv:
            deleted = clean_invalid_pdfs(directory)
            print(f"\n✅ 已删除 {len(deleted)} 个无效文件")
    else:
        print("✅ 所有 PDF 文件都有效!")
