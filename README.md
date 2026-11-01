# My AI Skills · AI 应用开发作品集

> 把学习路线上的每一个知识点，都做成能跑起来的小项目。

这个仓库收录了 **16 个可运行的 AI 应用与工程实践 demo**，覆盖从「调用大模型 API」到「本地部署模型」、从「Prompt 工程」到「多智能体编排」、从「扩散模型出图」到「语音克隆闭环」的完整链路。

**说明**：仓库只保留源码、Notebook 与文档，**不包含模型权重、数据集、虚拟环境和 `node_modules`**（这些文件动辄几个 GB，不适合进 Git）。每个项目的 README 里都写了怎么准备它们。

---

## 目录

| # | 项目 | 技术栈 | 一句话说明 |
|---|------|--------|-----------|
| 01 | [LLM 学习工作台](01-llm-knowledge-workspace/) | Gradio · LangChain · BeautifulSoup · SQLite · Svelte | 四标签页 LLM 应用：知识点扩充 / 论文生成 / 思维导图 / AI 写作，带登录鉴权与自定义 Gradio 组件 |
| 02 | [AI 智能编辑器](02-ai-editor-fullstack/) | Vue3 · Ant Design Vue · marked · FastAPI | 前后端分离的 Markdown 编辑器，一键 AI 润色且保持 Markdown 结构不变 |
| 03 | [ComfyUI Web 前端](03-comfyui-vue-webapp/) | Vue3 · Composition API · ComfyUI HTTP API | 给 ComfyUI 套一层干净的前端：线稿上色 + 参数可视化调节 |
| 04 | [SDXL 绘画应用](04-ai-painting-sdxl/) | diffusers · SDXL · Gradio · LangChain | 中文描述 → LLM 扩写成英文提示词 → 本地 SDXL 出图；含 5 个 diffusers 实验 Notebook |
| 05 | [Fabric.js AI 海报](05-fabric-ai-poster/) | Vue3 · Fabric.js v6 · Gradio | LLM 生成海报文案 JSON + 配图，Fabric 在浏览器里自动排版成海报 |
| 06 | [LangGraph 多智能体](06-langgraph-multi-agent/) | LangGraph · 本地 Qwen · SenseNova · SearXNG | 从单智能体 ReAct 到「主持人 + 多位明星」的综艺式多智能体协作 |
| 07 | [LangChain RAG 实战](07-langchain-rag/) | LangChain LCEL · FAISS · bge-large-zh · arxiv | 13 个 Notebook：向量检索、文档加载、工具调用、Shell 执行、完整 RAG 问答系统 |
| 08 | [TTS 语音机器人](08-tts-voice-robot/) | Coqui-TTS XTTS-v2 · Whisper · Gradio | 语音输入 → Whisper 识别 → LLM 回复 → XTTS-v2 用克隆音色说话，完整闭环 |
| 09 | [PyTorch 深度学习](09-pytorch-deep-learning/) | PyTorch · torchvision · CNN/RNN/GAN | CNN 手写识别、卫星图分类、VGG 迁移学习、目标定位与语义分割、文本分类、天气序列预测、GAN |
| 10 | [Flask AI 后端](10-flask-ai-backend/) | Flask · 智谱 GLM · SSE 流式 · SQLite | 从路由到流式响应的后端进阶，配套一套手写的前端聊天界面 |
| 11 | [爬虫与数据分析](11-web-scraping-data/) | requests · pyquery · Playwright · NumPy · pandas | 静态 + 动态页面抓取入库，再用 NumPy/pandas 做数据清洗与可视化 |
| 12 | [桌面应用开发](12-desktop-ai-app/) | tkinter / ttk · PyInstaller | tkinter 组件大全 + 三种布局 + 文件对话框 + Canvas，附打包成 exe 的配置 |
| 13 | [Web 前端基础](13-web-frontend-basics/) | HTML · CSS · JavaScript · Fetch · Promise | 从标签到异步请求的手写练习，最终落地为可交互的 AI 聊天界面 |
| 14 | [Gradio 界面开发](14-gradio-ui-basics/) | Gradio Blocks · ChatGLM3-6B · 自定义 CSS/JS | Blocks 布局、样式、自定义 JS、流式 Chatbot，以及本地 4bit 模型的角色扮演 |
| 15 | [Transformers 本地推理](15-transformers-basics/) | transformers · ChatGLM3 · Qwen | 本地加载并调用开源大模型，含流式输出与模型下载脚本 |
| 16 | [Flowise + VBA AI PPT](16-flowise-ppt-workflow/) | Flowise · 自定义 JS 节点 · PowerPoint VBA | 低代码编排工作流生成结构化 JSON，再由 PowerPoint 加载项自动排版成 PPT |

---

## 目录结构

```
My AI skills/
├── 01-llm-knowledge-workspace/      # LLM 应用（旗舰项目）
├── 02-ai-editor-fullstack/          # 全栈：Vue3 + FastAPI
├── 03-comfyui-vue-webapp/           # 全栈：Vue3 + ComfyUI
├── 04-ai-painting-sdxl/             # 生成式视觉：diffusers + Gradio
├── 05-fabric-ai-poster/             # 全栈：Fabric.js + Gradio
├── 06-langgraph-multi-agent/        # 智能体编排（Notebook）
├── 07-langchain-rag/                # RAG 与工具调用（Notebook）
├── 08-tts-voice-robot/              # 语音：ASR + TTS 闭环（Notebook）
├── 09-pytorch-deep-learning/        # 深度学习基础（Notebook）
├── 10-flask-ai-backend/             # 后端工程
├── 11-web-scraping-data/            # 爬虫与数据分析
├── 12-desktop-ai-app/               # 桌面端
├── 13-web-frontend-basics/          # 前端基础
├── 14-gradio-ui-basics/             # 界面开发（Notebook）
├── 15-transformers-basics/          # 本地模型推理
└── 16-flowise-ppt-workflow/         # 低代码工作流 + Office 自动化
```

编号按「AI 应用 → 算法 → 工程基础」排列，`01` ~ `08` 是更需要展示的项目。

---

## 快速开始

### 1. 准备 Python 环境

```powershell
# 推荐 Python 3.10+
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r <项目目录>/requirements.txt
```

### 2. 配置模型密钥

所有用到付费模型的代码都通过**环境变量**读取密钥，仓库里没有任何真实 Key：

```powershell
$env:SENSENOVA_API_KEY = "你的商汤 SenseNova Key"
$env:ZHIPU_API_KEY     = "你的智谱 Key"
```

也可以在项目目录下复制 `.env.example` 为 `.env` 再填写（`.env` 已被 `.gitignore` 忽略）。

| 环境变量 | 用途 | 涉及项目 |
|----------|------|---------|
| `SENSENOVA_API_KEY` | 商汤 SenseNova（OpenAI 兼容协议） | 01 / 02 / 04 / 05 / 06 / 08 / 16 |
| `ZHIPU_API_KEY` | 智谱 GLM | 10 |
| `SENIVERSE_API_KEY` | 心知天气 | 07 |
| `SDXL_DIR` | SDXL 模型目录（可选） | 04 |
| `FLOWISE_API_KEY` / `FLOWISE_DB` | Flowise 实例 | 16 |

### 3. 准备本地模型（按需）

用到本地权重的项目需要自己下载，仓库不含：

| 项目 | 需要的模型 | 说明 |
|------|-----------|------|
| 04 / 15 | `stable-diffusion-xl-base-1.0`、ChatGLM3-6B、Qwen | 放到项目 `models/` 下 |
| 06 / 07 / 14 | `Qwen1.5-1.8B`、`bge-large-zh-v1.5`、`ChatGLM3-6B` | 本地路径写在 Notebook 里，改成自己的即可 |
| 08 | `whisper-large-v3`、`XTTS-v2` | 首次运行会自动下载 |

### 4. 前端项目

```powershell
cd <项目目录>/<前端子目录>
npm install
npm run dev
```

---

## 关于这个仓库

- **代码全部为个人学习实践**，部分题目与业务灵感来自公开课程，实现、调试与文档由我完成。
- Notebook 中保留了运行输出（含图片），方便直接看效果；其中的绝对路径请按自己的环境调整。
- 迁移时已做**密钥脱敏**：所有硬编码 Key 都替换为 `os.getenv(...)`，本机绝对路径改为相对路径或环境变量。
- 提交历史按项目分阶段推送，方便回溯。

## License

个人学习项目，欢迎参考思路；转载或引用请注明出处。
