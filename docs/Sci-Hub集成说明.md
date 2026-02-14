# 📚 RIS 批量下载器 - Sci-Hub 版本

## ✅ 新功能

已成功集成 **Sci-Hub** 下载逻辑！

### 支持的下载源（按优先级）

1. **Unpaywall API** - 开放获取检测
2. **Sci-Hub ⚠️** - 绕过付费墙 (新增！)
3. **Semantic Scholar** - 微软学术搜索
4. **arXiv** - 预印本服务器
5. **CORE** - 开放获取论文库
6. **Open Access Button** - 开放获取按钮

---

## 🚀 使用方法

### 方式1: 批量下载 RIS 文件

```bash
python3 multi_source_ris_downloader.py savedrecs.ris
```

### 方式2: 测试 Sci-Hub 功能

```bash
python3 test_scihub.py "10.3390/pr8020248"
```

---

## ⚠️ Sci-Hub 使用说明

### 法律风险

- ⚠️ Sci-Hub 存在法律争议
- ⚠️ 请仅用于个人学习研究
- ⚠️ 不要用于商业目的
- ⚠️ 尊重版权和作者权益

### Sci-Hub 域名

脚本会依次尝试以下域名：

1. https://sci-hub.se
2. https://sci-hub.st
3. https://sci-hub.ru
4. https://sci-hub.wf
5. https://sci-hub.yt
6. https://sci-hub.do

### 下载机制

Sci-Hub 下载会尝试 3 种方法：

1. **查找 PDF 链接**
   - 在响应中搜索 `.pdf` 链接
   - 优先下载

2. **直接下载 PDF**
   - 检查响应 Content-Type
   - 如果是 PDF，直接保存

3. **查找嵌入 PDF**
   - 查找 `<embed src="...pdf">`
   - 下载嵌入的文件

---

## 📊 预期成功率

| 来源 | 预期成功率 | 说明 |
|------|------------|------|
| **Sci-Hub** | 60-70% | 大部分论文可下载 |
| **Unpaywall** | 20-30% | 开放获取文献 |
| **Semantic Scholar** | 15-20% | 部分开放获取 |
| **arXiv** | 10-15% | 物理数学计算机 |
| **CORE** | 10-15% | 开放获取 |
| **Open Access** | 5-10% | 完全开放 |

**总体预期成功率:** 70-80%

---

## 🎯 使用建议

### 推荐流程

```
1. 运行批量下载脚本
   python3 multi_source_ris_downloader.py savedrecs.ris

2. 脚本会自动尝试所有来源
   - Unpaywall API (优先)
   - Sci-Hub (新增！)
   - Semantic Scholar
   - 其他来源

3. 查看下载结果
   成功的 PDF 会在 ris_downloads/ 目录

4. 对于失败的文献
   - 使用提供的 Google Scholar 链接手动下载
   - 或使用 Sci-Hub 网站手动搜索
```

---

## 📁 文件说明

### 自动化脚本

1. **multi_source_ris_downloader.py**
   - 主批量下载脚本
   - 已集成 Sci-Hub
   - 支持多个来源

2. **test_scihub.py**
   - Sci-Hub 测试脚本
   - 用于验证功能

### 下载输出

```
ris_downloads/
├── *.pdf (已下载的 PDF 文件)
├── download_summary.txt (下载日志)
└── download_result.html (可视化结果)
```

---

## ⚠️ 注意事项

### 网络问题

- Sci-Hub 域名经常变化
- 部分域名可能不可用
- 脚本会自动尝试所有域名

### 速度问题

- Sci-Hub 有时响应较慢
- 建议设置较长的超时时间
- 可以减少并发请求数量

### 法律合规

- ✅ 优先使用合法渠道
- ✅ Sci-Hub 仅作为补充
- ✅ 尊重版权
- ✅ 合理使用

---

## 🔧 配置选项

### 修改超时时间

如果网络较慢，可以在脚本中修改超时：

```python
# 在 multi_source_ris_downloader.py 中
timeout=60  # 从 30 增加到 60 秒
```

### 修改下载目录

```python
# 在 __init__ 方法中
self.output_dir = "your_custom_directory"
```

### 添加更多 Sci-Hub 域名

```python
# 在 _try_scihub 方法中
scihub_domains = [
    'https://sci-hub.se',
    # 添加更多域名...
]
```

---

## 💡 故障排除

### 问题1: Sci-Hub 所有域名均不可用

**解决:**
- 等待一段时间后重试
- 手动访问 https://sci-hub.se/ 检查
- 使用备用域名

### 问题2: 下载速度很慢

**解决:**
- 检查网络连接
- 考虑使用代理
- 减少并发下载数量

### 问题3: 某些文献始终无法下载

**解决:**
- 可能文献不在 Sci-Hub 数据库中
- 使用 Google Scholar 手动搜索
- 联系作者获取

---

## 📝 总结

### 新增功能

✅ **集成 Sci-Hub 下载逻辑**
   - 支持多个 Sci-Hub 域名
   - 3 种下载方法
   - 自动错误处理

✅ **改进的批量下载**
   - 更好的错误处理
   - 详细的下载日志
   - 可视化结果页面

✅ **完整的使用文档**

### 使用建议

1. **立即可用**
   ```bash
   python3 multi_source_ris_downloader.py savedrecs.ris
   ```

2. **测试功能**
   ```bash
   python3 test_scihub.py "your-doi"
   ```

3. **查看结果**
   - 打开 `ris_downloads/` 目录
   - 查看 `download_result.html`

4. **手动补充**
   - 对于未下载的文献
   - 使用提供的链接手动下载

---

**更新日期:** 2026-02-11
**版本:** v2.0 (新增 Sci-Hub 支持)
**免责声明:** 请遵守版权法，Sci-Hub 存在法律风险