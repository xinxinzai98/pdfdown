#!/usr/bin/env python3
"""
RIS 文件多渠道批量下载器 (模块化版本 v4.0)

使用方法:
    python run_downloader.py [ris_file] [--workers N] [--retries N] [--config config.yaml]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import Config, MultiSourceDownloader, setup_logger


def main():
    parser = argparse.ArgumentParser(description="RIS 文件多渠道批量下载器 v4.0")
    parser.add_argument("ris_file", nargs="?", help="RIS 文件路径")
    parser.add_argument("--workers", type=int, default=3, help="最大并发数 (默认: 3)")
    parser.add_argument("--retries", type=int, default=2, help="最大重试次数 (默认: 2)")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--output", type=str, help="输出目录")
    parser.add_argument("--test", action="store_true", help="运行测试")

    args = parser.parse_args()

    if args.test:
        from tests import run_tests

        success = run_tests()
        sys.exit(0 if success else 1)

    if not args.ris_file:
        parser.print_help()
        print("\n示例:")
        print("  python run_downloader.py savedrecs.ris")
        print("  python run_downloader.py savedrecs.ris --workers 5 --retries 3")
        print("  python run_downloader.py --test")
        sys.exit(1)

    if not os.path.exists(args.ris_file):
        print(f"❌ 文件不存在: {args.ris_file}")
        sys.exit(1)

    config_path = args.config
    if not config_path:
        default_config = os.path.join(os.path.dirname(__file__), "config.yaml")
        if os.path.exists(default_config):
            config_path = default_config

    config = Config(config_path)

    if args.output:
        config._config["download"]["output_dir"] = args.output

    downloader = MultiSourceDownloader(
        config=config, max_workers=args.workers, max_retries=args.retries
    )

    downloader.batch_download_from_ris(args.ris_file)


if __name__ == "__main__":
    main()
