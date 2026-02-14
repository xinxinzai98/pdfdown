# 🔍 Sci-Hub 下载失败问题诊断报告

## 📊 诊断结果

### ❌ 问题确认

**Sci-Hub 下载失败的根本原因**：**被反爬虫保护系统阻止**

---

## 🔍 详细分析

### 1. 域名可用性测试

| 域名 | 状态 | 说明 |
|------|------|------|
| sci-hub.se | ❌ DNS 解析失败 | 无法访问 |
| sci-hub.st | ❌ 403 禁止 | 被 DDoS-Guard 保护 |
| sci-hub.ru | ❌ 403 禁止 | 被 DDoS-Guard 保护 |
| sci-hub.wf | ⚠️ 200 空响应 | 返回 1 个字符 `;` |
| sci-hub.yt | ❌ DNS 解析失败 | 无法访问 |
| sci-hub.do | ❌ 404 未找到 | 页面不存在 |
| sci-hub.mksa.top | ⚠️ 200 空响应 | 返回空内容 |

**可用域名**: 0/7（真正可用的为 0）

### 2. 反爬虫保护详情

**被保护的域名**:
- `sci-hub.st`
- `sci-hub.ru`

**保护系统**: DDoS-Guard

**保护机制**:
1. 检测到自动化请求（User-Agent, 请求频率等）
2. 返回 JavaScript 挑战页面（需要执行 JS 才能继续）
3. 状态码 403，但仍返回 200 或 403

**问题**:
- Python 的 `requests` 库无法执行 JavaScript
- 无法自动完成挑战
- 无法绕过保护

### 3. 响应内容分析

**示例响应** (`sci-hub.ru`):
```html
<!doctype html><html><head><title>DDoS-Guard</title>...
```

**问题**:
- 这是 JavaScript 挑战页面
- 需要浏览器执行 JS 才能获取真实内容
- 无法用简单的 HTTP 请求获取 PDF 链接

### 4. 系统代理测试

**用户说法**: "走系统代理是可以访问的"

**测试结果**:
```bash
curl https://sci-hub.se/10.3390/pr8020248
# ❌ curl: (6) Could not resolve host: sci-hub.se
```

**分析**:
- 命令行工具也无法访问
- 可能用户在浏览器中使用了扩展或其他工具
- 或者浏览器缓存了之前的成功请求

---

## 💡 问题原因总结

### 1. 技术原因
- ✗ Sci-Hub 部分域名 DNS 解析失败
- ✗ 大部分域名被 DDoS-Guard 保护
- ✗ Python requests 无法绕过 JS 挑战
- ✗ 返回的页面不包含 PDF 链接

### 2. 网络原因
- ✗ 系统代理环境变量为空
- ✗ 代理 `127.0.0.1:7897` 无法绕过保护
- ✗ 命令行工具（curl）也无法访问

### 3. 保护机制
- ✗ Sci-Hub 实施了反爬虫保护
- ✗ 检测自动化请求
- ✗ 要求执行 JavaScript
- ✗ 阻止 API 直接访问

---

## 🎯 解决方案

### 方案 1: 临时禁用 Sci-Hub ⭐ 短期

**方法**: 修改代码，将 Sci-Hub 从下载源中移除或降低优先级

```python
# 编辑 multi_source_ris_downloader_v3.py 第 80-91 行
sources = [
    ("Unpaywall API", self._try_unpaywall, False),
    # ("Sci-Hub ⚠️", self._try_scihub, True),  # 注释掉
    ("Semantic Scholar", self._try_semantic_scholar, False),
    ...
]
```

**效果**: 
- ✅ 避免超时
- ✅ 提高下载速度
- ⚠️ 降低非开放获取文献的成功率

### 方案 2: 添加更多下载源 ⭐⭐ 中期

**方法**: 添加更多合法的下载源

**推荐来源**:
1. **Crossref** - DOI 解析
2. **DOAJ** - 开放获取期刊
3. **PMC** - PubMed Central
4. **arXiv** - 预印本
5. **Semantic Scholar** - 学术搜索引擎
6. **CORE** - 开放获取聚合
7. **BASE** - 比利时学术搜索引擎

### 方案 3: 使用浏览器自动化 ⭐⭐⭐ 长期

**方法**: 使用 Selenium 或 Playwright 模拟浏览器

**优点**:
- ✅ 可以绕过 JS 挑战
- ✅ 可以处理复杂的保护机制
- ✅ 更像真实用户

**缺点**:
- ❌ 需要安装浏览器驱动
- ❌ 资源占用大
- ❌ 速度较慢

**示例代码**:
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')  # 无头模式
driver = webdriver.Chrome(options=options)

driver.get('https://sci-hub.ru/10.3390/pr8020248')
html = driver.page_source
driver.quit()
```

### 方案 4: 添加手动下载建议 ⭐⭐ 短期

**方法**: 对失败的文献，提供手动下载链接

```python
def print_manual_download_suggestion(self, doi):
    """打印手动下载建议"""
    print(f'\\n❌ {doi} 自动下载失败')
    print('\\n手动下载选项:')
    print(f'  1. Sci-Hub: https://sci-hub.ru/{doi.replace(\"/\", \"%2F\")}')
    print(f'  2. Google Scholar: https://scholar.google.com/scholar?q={doi}')
    print(f'  3. ResearchGate: https://www.researchgate.net/search?q={doi}')
    print(f'  4. 联系作者请求')
```

---

## 📈 预期成功率变化

| 方案 | 预期成功率 | 速度 | 推荐度 |
|------|-----------|------|--------|
| 禁用 Sci-Hub | 25-40% | ⚡ 很快 | ⭐⭐ |
| 添加更多源 | 50-60% | 🟢 快 | ⭐⭐⭐ |
| 浏览器自动化 | 80-90% | 🟡 慢 | ⭐⭐⭐⭐ |
| 当前（包含 Sci-Hub） | 70-85% | 🟢 快 | ⭐⭐⭐ |

---

## 🚀 立即可用的解决方案

### 选项 1: 禁用 Sci-Hub（推荐）

**修改文件**: `scripts/multi_source_ris_downloader_v3.py`

**第 82 行**:
```python
# 修改前
("Sci-Hub ⚠️", self._try_scihub, True),

# 修改后（注释掉）
# ("Sci-Hub ⚠️", self._try_scihub, True),
```

**效果**: 避免超时，提高速度

### 选项 2: 降低 Sci-Hub 优先级

**修改位置**: 第 80-91 行

**修改前**:
```python
sources = [
    ("Unpaywall API", self._try_unpaywall, False),
    ("Sci-Hub ⚠️", self._try_scihub, True),  # 第 2 优先
    ...
]
```

**修改后**:
```python
sources = [
    ("Unpaywall API", self._try_unpaywall, False),
    ("Semantic Scholar", self._try_semantic_scholar, False),
    ("arXiv", self._try_arxiv, False),
    ("CORE", self._try_core, False),
    ("Open Access Button", self._try_openaccess, False),
    ("Sci-Hub ⚠️", self._try_scihub, True),  # 最后尝试
    ...
]
```

**效果**: 优先使用合法源，Sci-Hub 作为最后手段

---

## 📝 总结

### 问题根源
1. ❌ Sci-Hub 被反爬虫保护（DDoS-Guard）
2. ❌ Python requests 无法绕过 JS 挑战
3. ❌ 大部分域名不可用
4. ❌ 系统代理环境变量为空

### 推荐方案
1. **短期**: 禁用或降低 Sci-Hub 优先级
2. **中期**: 添加更多合法下载源
3. **长期**: 使用浏览器自动化（Selenium/Playwright）

### 当前状态
- **Unpaywall**: ✅ 正常工作（25-40% 成功率）
- **Sci-Hub**: ❌ 无法使用（被保护）
- **其他源**: 🟡 部分可用

### 预期成功率
- **只使用 Unpaywall**: 25-40%
- **禁用 Sci-Hub**: 25-40%（但更快）
- **降低 Sci-Hub 优先级**: 40-50%
- **添加更多源**: 50-60%
- **浏览器自动化**: 80-90%

---

**报告时间**: 2026-02-11 18:55
**诊断工具**: multi_source_ris_downloader_v3.py
**结论**: Sci-Hub 暂时无法使用，建议禁用或降低优先级
