# 01 · LLM 学习工作台（Gradio 多标签页应用）

> 用一个 Gradio 应用把「读资料 → 写论文 → 画导图 → 改文稿」串成一条完整的内容生产流水线。

## 技术栈

`Python` · `Gradio Blocks/Tabs` · `LangChain (ChatOpenAI)` · `商汤 SenseNova` · `BeautifulSoup` · `markmap` · `SQLite` · `Svelte + Vite`（自定义 Gradio 组件）

## 四个标签页

| 标签页 | 做什么 | 关键实现 |
|--------|--------|---------|
| 📎 知识点扩充 | 读取数学可视化 HTML → 提取 meta/正文 → 生成 Markdown 知识点文档 | BeautifulSoup 解析 + 结构化 Prompt，输出固定五段式结构 |
| 📑 论文生成 | 选题 → 生成大纲 → 逐章撰写 → 阅读文献提取论点 | 多轮有状态调用，章节独立生成避免超长上下文 |
| 🧠 思维导图 | 生成 Markmap Markdown 并实时渲染 | 通过 `gr.HTML` + 动态注入 markmap CDN 脚本 |
| ✍️ AI 写作助手 | 续写 / 润色 / 生成标题，供 Vue 前端跨域调用 | 独立的 API 入口，配合 02 项目的编辑器 |

## 目录结构

```
01-llm-knowledge-workspace/
├── server.py                 # 主入口：页面框架 + 登录鉴权 + 启动
├── component/
│   ├── tab1.py ~ tab4.py     # 四个标签页，各自暴露 create_tab()
│   └── mycomponent/          # 自研 Gradio 自定义组件（Svelte 前端 + Python 后端）
├── db/
│   └── init_db.py            # 初始化 SQLite 用户表（首次运行）
├── sample_docs/
│   ├── math/                 # 44 个数学可视化 HTML（tab1 的输入素材）
│   └── papers/               # 放你自己的论文 PDF（tab2 的阅读素材）
└── knowledge_docs/           # 生成的知识点文档示例
```

## 运行

```powershell
# 1) 激活虚拟环境并装依赖
pip install -r requirements.txt

# 2) 初始化数据库（只需一次）
python db/init_db.py

# 3) 配置密钥
$env:SENSENOVA_API_KEY = "你的 Key"

# 4) 启动
python server.py
# 浏览器打开 http://127.0.0.1:7860
```

默认演示账号：`admin / 123456`（见 `db/init_db.py`，可自行修改）。

## 实现要点

- **模块化页签架构**：`server.py` 只负责搭框架，新增功能只需添加 `component/tabN.py` 并实现 `create_tab()`，不用改动已有代码。
- **端口占用检测**：启动前用 socket 试探端口，被占用时给出明确提示，而不是抛一屏报错。
- **登录鉴权**：`demo.launch(auth=auth)` 接入自定义回调，账号密码走 SQLite 参数化查询，防注入。
- **自定义 Gradio 组件**：`component/mycomponent/` 是一个可独立安装的 Gradio 组件包（Python 后端 + Svelte 前端），演示了组件的注册与打包方式。
- **失败降级**：LLM 调用带超时与重试，失败时回退到本地拼接结果，保证流程不中断。
