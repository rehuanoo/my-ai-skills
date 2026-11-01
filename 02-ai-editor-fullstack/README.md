# 02 · AI 智能编辑器（Vue3 + FastAPI 全栈）

> 左边写 Markdown，右边实时预览；写完点一下「AI 润色」，文字变流畅但排版结构一个字节都不动。

## 技术栈

**前端**：`Vue3 (script setup)` · `Ant Design Vue` · `marked (GFM)` · `Vite`
**后端**：`FastAPI` · `uvicorn` · `Pydantic` · `langchain_openai` · `CORS`

## 功能

- Markdown 双栏编辑：左侧输入，右侧用 `marked` 实时渲染（支持表格 / 任务列表 / 删除线）
- 载入本地 `.md` 文件（`beforeUpload` 返回 `false` 阻止真实上传）、载入内置示例
- 底部状态栏实时统计字符数与行数
- **AI 润色**：把整篇 Markdown 交给大模型，要求「只优化文字表达，标题层级 / 列表 / 表格 / 代码块 / 引用一律原样保留」
- 一键复制渲染后的 HTML

## 目录结构

```
02-ai-editor-fullstack/
├── AI_editor/                 # 前端（Vue3 + Vite）
│   └── src/
│       ├── App.vue            # 主界面：编辑器 + 预览 + 润色
│       ├── App基本的使用.vue    # Vue3 语法基础练习
│       └── components/
└── Ai_editor_server/
    └── server.py              # 后端：POST /polish
```

## 运行

```powershell
# 后端（先跑）
cd Ai_editor_server
$env:SENSENOVA_API_KEY = "你的 Key"
python server.py            # http://127.0.0.1:8000

# 前端（另开一个终端）
cd AI_editor
npm install
npm run dev                 # http://127.0.0.1:5173
```

## 实现要点

- **提示词约束结构**：Markdown 是最容易被 LLM「顺手改坏」的格式，所以重新润色的 Prompt 里明确列出「保留清单」，并把温度调到 0.4 保证风格稳定。
- **跨域**：Vue dev server 跑在 5173、后端在 8000，`CORSMiddleware` 放开本地调试所需的方法与头。
- **错误处理**：后端对模型异常返回结构化错误，前端用 `message.error` 提示，不吞异常。
- **可复用**：同一个 `server.py` 也能被 01 项目的 Gradio 页签通过 HTTP 调用。
