# 📚 学术文献批量下载工具 v4.0

## 📋 简介

这是一个用于从 RIS 文件批量下载学术文献 PDF 的工具集。

### ✅ v4.0 新特性 (模块化重构)

- 🏗️ **模块化架构** - 代码拆分为独立的模块，易于维护和扩展
- 📝 **类型提示** - 完整的类型注解，提高代码质量
- ⚙️ **配置管理** - 统一使用 config.yaml 配置文件
- 📊 **日志系统** - 使用 Python logging 模块
- 🔒 **安全修复** - HTML 报告转义防止 XSS
- 🧪 **单元测试** - 32 个测试用例确保代码质量

### 🎯 下载源（按优先级）

1. **Unpaywall API** - 开放获取检测（合法）
2. **Sci-Hub ⚠️** - 绕过付费墙（谨慎使用）
3. **Semantic Scholar** - 微软学术搜索
4. **arXiv** - 预印本服务器
5. **CORE** - 开放获取论文库
6. **Open Access Button** - 开放获取检测
7. **Europe PMC** - 生物医学文献
8. **PubMed** - 医学文献
9. **Paperity** - 开放获取平台
10. **Google Scholar** - 学术搜索
11. **ResearchGate** - 学术社交网络

---

## 📁 文件结构

```
PaperDownloader/
├── lib/                          # 核心库
│   ├── __init__.py
│   ├── core/                     # 核心模块
│   │   ├── __init__.py
│   │   └── downloader.py         # 主下载器
│   ├── sources/                  # 下载源模块
│   │   ├── __init__.py
│   │   ├── base.py               # 下载源基类
│   │   ├── unpaywall.py          # Unpaywall 源
│   │   ├── scihub.py             # Sci-Hub 源
│   │   └── others.py             # 其他源
│   └── utils/                    # 工具模块
│       ├── __init__.py
│       ├── config.py             # 配置管理
│       ├── logger.py             # 日志系统
│       ├── validator.py          # PDF 验证
│       └── report.py             # HTML 报告生成
│
├── tests/                        # 单元测试
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_validator.py
│   ├── test_report.py
│   ├── test_sources.py
│   └── test_downloader.py
│
├── scripts/                      # 旧版脚本（保留兼容）
├── config.yaml                   # 配置文件
├── run_downloader.py             # 主入口
└── README.md
```

---

## 🚀 快速开始

### 安装依赖

```bash
pip3 install pyyaml beautifulsoup4 requests
```

### 运行测试

```bash
python3 run_downloader.py --test
```

### 批量下载

```bash
# 基本用法
python3 run_downloader.py savedrecs.ris

# 自定义参数
python3 run_downloader.py savedrecs.ris --workers 5 --retries 3

# 指定配置文件
python3 run_downloader.py savedrecs.ris --config config.yaml

# 指定输出目录
python3 run_downloader.py savedrecs.ris --output my_downloads
```

---

## ⚙️ 配置说明

编辑 `config.yaml`:

```yaml
# 代理配置
proxy:
  overseas:
    http: "http://127.0.0.1:7897"
    https: "http://127.0.0.1:7897"
  china_network: null

# 下载配置
download:
  output_dir: "ris_downloads"
  max_workers: 3
  max_retries: 2
  timeout: 30
  validate_pdf: true

# 下载源配置
sources:
  priority:
    - Unpaywall
    - Sci-Hub
    - Semantic Scholar
    # ...
  
  Unpaywall:
    enabled: true
    email: "your@email.com"
  
  Sci-Hub:
    enabled: true
    domains:
      - "https://sci-hub.se"
      # ...
```

---

## 🧪 测试覆盖

| 模块 | 测试数 |
|------|--------|
| 配置管理 (config) | 7 |
| PDF 验证 (validator) | 8 |
| HTML 报告 (report) | 5 |
| 下载源 (sources) | 8 |
| 下载器 (downloader) | 4 |
| **总计** | **32** |

---

## 📊 代码改进

### v4.0 vs v3.0

| 改进项 | v3.0 | v4.0 |
|--------|------|------|
| 模块化 | 单文件 1141 行 | 10+ 个模块 |
| 类型提示 | 无 | 完整 |
| 配置管理 | 硬编码 | YAML 配置 |
| 日志系统 | print | logging |
| 单元测试 | 无 | 32 个测试 |
| HTML 安全 | 未转义 | 已转义 |

---

## 📖 API 使用

```python
from lib import Config, MultiSourceDownloader

# 创建配置
config = Config("config.yaml")

# 创建下载器
downloader = MultiSourceDownloader(
    config=config,
    max_workers=5,
    max_retries=3
)

# 批量下载
downloader.batch_download_from_ris("savedrecs.ris")
```

---

## 🌐 浏览器下载工具

对于动态加载的页面（如新版 Sci-Hub），可以使用浏览器自动化工具：

### 安装 Playwright

```bash
pip install playwright
playwright install chromium
```

### 使用方法

```bash
# 自动模式（无界面）
python3 browser_download.py 10.1021/acsami.1c08462 --output ris_downloads

# 交互模式（显示浏览器窗口，手动通过验证）
python3 browser_download.py 10.1021/acsami.1c08462 --interactive --wait 30 --output ris_downloads

# 使用自定义代理
python3 browser_download.py 10.1021/acsami.1c08462 --proxy socks5://127.0.0.1:7897
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--interactive` / `-i` | 交互模式，显示浏览器窗口，需要手动通过 DDoS 验证 |
| `--wait` | 交互模式等待时间（秒），默认 30 |
| `--proxy` | 代理服务器地址 |
| `--output` / `-o` | 输出目录 |

---

## ⚠️ 重要说明

### 合法使用

1. **优先使用合法渠道**
   - 图书馆订阅
   - 开放获取资源
   - Unpaywall API

2. **谨慎使用 Sci-Hub**
   - ⚠️ 存在法律争议
   - 仅用于个人学习研究
   - 不要商业用途

---

## 📝 更新日志

### v4.1 (2026-02-14)

- ✅ 添加浏览器自动化下载工具 (Playwright)
- ✅ 支持交互模式手动通过 DDoS 验证
- ✅ Sci-Hub 添加代理支持
- ✅ HTML 报告增加官方下载通道链接
- ✅ 修复配置文件自动加载问题

### v4.0 (2026-02-14)

- ✅ 完全模块化重构
- ✅ 添加类型提示
- ✅ 统一配置管理
- ✅ 改进日志系统
- ✅ 修复 HTML 转义问题
- ✅ 添加 32 个单元测试
- ✅ 所有测试通过

### v3.0 (2026-02-11)

- ✅ 并发下载
- ✅ HTML 报告
- ✅ 代理支持

### v2.0 (2026-02-11)

- ✅ Sci-Hub 集成
- ✅ 多源下载

---

**版本:** 4.0
**更新日期:** 2026-02-14
**Python 要求:** 3.7+
**依赖:** requests, pyyaml, beautifulsoup4
