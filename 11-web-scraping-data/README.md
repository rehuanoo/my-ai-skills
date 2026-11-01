# 11 · 爬虫与数据分析

> 把网页上的数据抓下来存进数据库，再用 pandas 把它变成结论。

## 技术栈

`requests` · `pyquery` · `Playwright`（动态渲染）· `SQLite` · `NumPy` · `pandas` · `matplotlib`

## 内容

### 爬虫（`01.pyquery`）

| 文件 | 说明 |
|------|------|
| `spider.py` / `spider1.py` | 静态页面抓取：`requests` + `pyquery` 解析，入库 SQLite |
| `spider2.py` | 动态页面：用 `Playwright` 驱动浏览器抓渲染后的 DOM |
| `download.py` | 批量下载图片资源，带重试与防重名 |
| `database/herolist.db` | 抓取结果（SQLite，3 张关联表；运行后自动生成，未提交） |

抓取目标是一家游戏官网的英雄资料页，练习点在于：分页、相对链接补全、随机延时、图片落地。

### 登录态抓取（`02.获取登录数据`）
用 `requests.Session` 保持 cookie，模拟登录后访问需要鉴权的页面。

### 数据分析

- `03.numpy`：数组创建 / 索引切片（含高级索引）/ 轴方向 / 字符串向量化 / 保存读取 `.npy` `.npz`
- `04.pandas`：DataFrame 基本操作、缺失值处理、`apply` 与字符串方法、**窗口函数**、**时间序列**、数据可视化

## 运行

```powershell
pip install -r requirements.txt
playwright install chromium     # 动态抓取需要浏览器内核

cd 01.pyquery
python spider2.py
```

## 实现要点

- **防封**：带 `User-Agent`、请求间随机 sleep、失败重试；`encoding` 显式设成 `utf-8` 解决中文乱码。
- **数据清洗**：抓下来的文本先用正则去空白与特殊字符，再入库。
- **时间序列**：`resample` / `rolling` / 窗口函数的对比与适用场景。
