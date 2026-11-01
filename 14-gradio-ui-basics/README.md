# 14 · Gradio 界面开发

> Gradio 不只是 `gr.Interface` 三行代码，Blocks 能做出真正像样的产品界面。

## 技术栈

`Gradio (Blocks / Tabs / Row / Column)` · `自定义 CSS / JS` · `ChatGLM3-6B (4-bit)` · `transformers` · `TextIteratorStreamer`

## Notebook 清单

| 文件 | 内容 |
|------|------|
| `01.Gradio.ipynb` | `gr.Interface` 与 `gr.Blocks` 的区别、输入输出组件 |
| `02.radio固定计划运行.ipynb` | 定时任务与计划运行 |
| `03.布局.ipynb` | `Row` / `Column` / `Tabs` / `Accordion` 组合出复杂布局 |
| `04.css样式.ipynb` | `css=` 自定义样式，改字体、颜色、间距 |
| `05.自定义js.ipynb` | `js=` 注入前端逻辑（滚动、快捷键、剪贴板） |
| `06.聊天机器人.ipynb` / `06.聊天机器人new.ipynb` | ChatGLM3-6B 角色扮演聊天：4-bit 量化 + 流式输出 |
| `08.提示词工程.ipynb` | 系统提示词、角色设定、few-shot 的影响 |
| `snake.py` | 用 Gradio 做的小游戏（事件与状态管理练习） |

## 运行

```powershell
pip install -r requirements.txt
# 06 需要本地 ChatGLM3-6B（4-bit 约 3.8GB 显存）
```

## 实现要点

- **4-bit 量化**：`load_in_4bit` + `bnb_4bit_compute_dtype`，6B 模型塞进 8GB 显卡，全部放 GPU 不做 CPU offload。
- **流式输出**：`TextIteratorStreamer` + 子线程 `generate`，前端逐字出现。
- **历史管理**：Gradio 6.x 会把 `content` 转成 list 格式导致 ChatGLM 报错，所以自己维护 `chat_history`，界面用的 history 和模型输入的历史分开存。
- **中文路径**：SentencePiece 不支持中文路径，用虚拟盘映射绕过（代码有注释）。
