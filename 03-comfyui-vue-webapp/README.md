# 03 · AI 实时绘画 Web（Vue3 + ComfyUI）

> 上传一张线稿，AI 按你的中文提示词给它上色 —— 前端只管体验，算力交给本地 ComfyUI。

## 技术栈

`Vue3 (Composition API)` · `ref / reactive` · `Fetch API` · `FileReader (base64)` · `ComfyUI HTTP API`

## 功能

- 中文提示词 + 反向提示词输入
- 线稿图片上传与预览（`FileReader` 转 base64 → 直接随请求体传输，无需先落盘）
- 滑块实时调节：生成步数（1–20）、CFG 引导强度、ControlNet 强度、随机种子
- 一键随机种子，可复现同一张图
- 加载态、错误态与后端返回的 `details` 字段联动提示

## 目录结构

```
03-comfyui-vue-webapp/
└── comfyuiApp/
    ├── src/
    │   ├── App.vue          # 全部逻辑与界面
    │   ├── style.css
    │   └── main.js
    ├── index.html
    ├── vite.config.js
    └── package.json
```

## 与后端的约定

前端向 `http://127.0.0.1:9888/api/generate` 发 POST：

```json
{
  "prompt": "一只可爱的猫, 彩色插画, 高质量",
  "negative_prompt": "低质量, 模糊",
  "steps": 6,
  "cfg": 1.5,
  "seed": 42,
  "cn_strength": 0.85,
  "sketch": "data:image/png;base64,...."
}
```

成功返回 `{ "success": true, "image": "<base64>" }`，失败返回 `{ "error": "...", "details": "..." }`。
后端是基于 ComfyUI 工作流封装的薄服务层（LCM 少步采样 + ControlNet 线稿控制）。

## 运行

```powershell
# 1) 先启动 ComfyUI 及其封装 API（默认 9888 端口）
# 2) 再启动前端
cd comfyuiApp
npm install
npm run dev
```

> 后端服务地址写在 `src/App.vue` 的 `API_BASE` 常量里，换环境时改这一行即可。
