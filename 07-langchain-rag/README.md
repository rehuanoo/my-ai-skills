# 07 · LangChain RAG 实战（13 个 Notebook）

> 把「检索 → 提示词 → 大模型」这条链路拆开揉碎，最后拼成一个能回答私有文档问题的 RAG 系统。

## 技术栈

`LangChain (LCEL)` · `FAISS` · `bge-large-zh-v1.5`（本地 Embedding）· `WebBaseLoader` · `arxiv` · `ChatGLM3` 本地 API · `SearXNG` / `Fess` 搜索

## Notebook 清单

| 文件 | 内容 |
|------|------|
| `01.Langchain.ipynb` | 模型接入、Prompt 模板、输出解析器、LCEL 管道 |
| `02.向量存储和数据检索.ipynb` | Embedding 原理、相似度检索、向量库读写 |
| `03.文档加载器.ipynb` | 各类 Loader：文本 / PDF / 网页 / 目录 |
| `04.a付费模型接入Langchain.ipynb` | 用 OpenAI 兼容协议接入第三方付费模型 |
| `04.RAG问答系统.ipynb` | **完整 RAG**：WebBaseLoader → 分块 → FAISS → 检索 → 组装上下文 → 回答 |
| `05.Langchain调用工具.ipynb` | Tool / Agent：让模型自己决定调哪个工具（天气、搜索） |
| `06.fess文档搜索服务器.ipynb`、`06.fess，api接口搜索.ipynb` | 企业级搜索服务 Fess 的接入 |
| `07.调用shell执行终端命令.ipynb` | 给模型一个 Shell 工具（含安全边界讨论） |
| `10.扩充知识库.ipynb` | 把 44 个数学可视化 HTML 批量转成知识库文档 |
| `11.Langchain本地模型api调用.ipynb` | 本地 ChatGLM3 的 OpenAI 兼容接口 |
| `12.论文加载arxiv.ipynb` | 按关键词检索 arXiv 论文并下载 |

## 目录结构

```
07-langchain-rag/
├── 01 ~ 12.*.ipynb
├── txt/                    # 检索语料：华为资料 + 44 个数学可视化 HTML
├── article_333623112.txt   # RAG 用的知乎文章缓存
└── arxiv_papers/           # 运行 12 号 notebook 后会生成（.gitignore 已忽略 PDF）
```

## 环境要求

- 本地 Embedding：`bge-large-zh-v1.5`（约 1.3GB），路径写在 Notebook 里
- 可选：本地 ChatGLM3 的 OpenAI 兼容服务，或直接用付费 API
- `$env:SENIVERSE_API_KEY`（05 号 Notebook 的天气工具）

## 实现要点

- **RAG 三步走**：`RecursiveCharacterTextSplitter`（chunk 300 / overlap 50）→ FAISS 建库 → `as_retriever()` + LCEL 拼成链。
- **反爬兜底**：知乎会返回 403，`WebBaseLoader` 失败或正文过短时自动回退到本地缓存文件，保证 Notebook 可复现。
- **提示词约束**：RAG 的 Prompt 明确要求「只依据检索到的资料回答，资料里没有就说不知道」，减少幻觉。
- **中文路径问题**：部分 Tokenizer（SentencePiece）不支持中文路径，Notebook 里用虚拟盘映射解决，代码有注释说明。
