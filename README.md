# PDF 下载器

多渠道学术论文 PDF 下载工具，支持 RIS 文件批量下载。

## 功能

- **第一阶段**: 公开渠道 (Unpaywall + CORE)
- **第二阶段**: 浏览器官方渠道 (Wiley, Elsevier, MDPI, ACS, Springer)

## 快速开始

```bash
# 完整流程
python3 full_pipeline.py savedrecs.ris -o ./downloads

# 仅公开渠道
python3 full_pipeline.py savedrecs.ris --skip-browser -o ./downloads

# 仅浏览器 (需要先启动 Edge CDP)
python3 full_pipeline.py savedrecs.ris --skip-public -o ./downloads
```

## 浏览器 CDP 模式

对于需要登录的出版商（Wiley, Elsevier 等），使用浏览器 CDP 模式：

```bash
# 1. 启动 Edge 浏览器
open -na "Microsoft Edge" --args \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/edge-cdp-profile \
  --no-proxy-server \
  --no-first-run --no-default-browser-check

# 2. 在浏览器中登录需要的出版商

# 3. 运行下载
python3 full_pipeline.py savedrecs.ris -o ./downloads
```

## 文件结构

```
04_PaperDownloader/
├── full_pipeline.py      # 主程序 (两阶段下载)
├── run_downloader.py     # 旧版多渠道下载器
├── wiley_downloader.py   # Wiley 专用下载器
├── config.yaml           # 配置文件
├── savedrecs.ris         # 测试 RIS 文件
├── lib/                  # 核心库
│   ├── core/            # 下载核心
│   ├── sources/         # 下载源
│   └── utils/           # 工具
├── tests/               # 测试
├── docs/                # 文档
└── downloads/           # 下载输出
```

## 支持的出版商

| 出版商 | 公开渠道 | 浏览器 CDP |
|--------|---------|-----------|
| Wiley  | ✅      | ✅        |
| Elsevier | ❌/✅  | ⚠️ 需登录 |
| MDPI   | ✅      | ⚠️ 部分   |
| ACS    | ✅      | ✅        |
| Springer | ✅    | ✅        |

## 依赖

```bash
pip install requests playwright
playwright install chromium
```
