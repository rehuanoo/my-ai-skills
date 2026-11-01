# 05 · AI 海报生成器（Fabric.js + Gradio）

> 告诉 AI「给我做一张王楚钦夺冠的体育风海报」，它负责写文案、画配图，浏览器里的 Fabric 负责排版。

## 技术栈

**后端**：`Gradio` · `requests` · `Pillow` · 商汤 SenseNova（`sensenova-6.8-flash-lite` 写文案 + `u1.5-lite` 文生图）
**前端**：`Vue3` · `Fabric.js v6` · `@gradio/client` · `Vite`

## 工作流

```
用户中文需求
   ↓ LLM 输出严格 JSON：{title, title_en, tagline, points[], footer, image_prompt}
   ↓ 文生图模型按 image_prompt 画一张竖版配图
   ↓ 前端拿到文案 + 图片，Fabric.js 自动排版成 800 × 1120 海报
   ↓ 用户可继续拖动 / 修改 / 导出 PNG
```

## 目录结构

```
05-fabric-ai-poster/
├── server/
│   └── server.py             # Gradio 后端：/generate_poster
├── vite-poster/
│   ├── src/
│   │   ├── App.vue           # 界面：输入需求 → 调后端 → 渲染海报
│   │   └── poster.js         # 排版核心：buildPoster(fabric, canvas, {data})
│   └── public/imgs/          # 底图与人像素材
└── package.json
```

## 运行

```powershell
# 后端
cd server
$env:SENSENOVA_API_KEY = "你的 Key"
python server.py            # http://127.0.0.1:7864

# 前端
cd vite-poster
npm install
npm run dev
```

## 实现要点

- **强制 JSON 输出**：Prompt 里逐字段约定类型与字数，后端再用正则兜底剥掉多余的解释文字，避免解析失败。
- **字号自适应**：`poster.js` 按文本长度动态算字号，保证长短标题都不溢出、不换行错位。
- **Fabric v6 的坑**：v6 起 `originX/originY` 默认是 `center`，所有元素必须显式 `set({originX:'left', originY:'top'})`，否则整体错位 —— 这个修复在代码注释里有记录。
- **双端复用**：`poster.js` 同时被浏览器（`import 'fabric'`）和 Node 预览脚本（`fabric/node`）使用，因此 `fabric` 实例由调用方注入，不写死 import。
- **装饰元素锁定**：背景与修饰层设为 `selectable: false`，只让用户编辑文字，避免误拖。
