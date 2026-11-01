# 15 · Transformers 本地模型推理

> 不通过 API，直接把开源大模型加载到自己的显卡上跑起来。

## 技术栈

`transformers` · `torch` · `ChatGLM3-6B` · `Qwen1.5-1.8B`

## 文件

| 文件 | 说明 |
|------|------|
| `dowmloadModel.py` | 从 HuggingFace 拉取模型到本地目录（支持镜像） |
| `test.py` | 加载模型并做一次完整推理：`AutoTokenizer` + `AutoModelForCausalLM` + `generate` |
| `test_stream.py` | 流式推理：`TextIteratorStreamer` + 子线程，逐 token 输出 |

## 运行

```powershell
pip install -r requirements.txt

# 1) 下载模型（或在 HuggingFace 网页手动下载后放到 models/ 下）
python dowmloadModel.py

# 2) 单次推理
python test.py

# 3) 流式输出
python test_stream.py
```

模型默认放在 `models/` 目录（已被 `.gitignore` 忽略，不会进仓库）。

## 实现要点

- **显存控制**：`torch_dtype=torch.float16` + `device_map="auto"`，显存不够时自动拆分到 CPU。
- **流式**：`TextIteratorStreamer` 配合 `threading.Thread` 启动 `model.generate`，主线程迭代读取。
- **两种模型的差异**：ChatGLM 用 `trust_remote_code=True` 的自定义类，Qwen 用标准 `AutoModelForCausalLM` —— 代码里两种写法都有。
