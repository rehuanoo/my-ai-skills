# 04 · SDXL 绘画应用（diffusers + Gradio）

> 用中文描述画面，让大模型把它扩写成专业的英文提示词，再交给本地 SDXL 出图。

## 技术栈

`diffusers` · `StableDiffusionXL (fp16)` · `PyTorch` · `Gradio` · `LangChain / ChatOpenAI`（提示词翻译扩写）

## 两部分内容

### 一、5 个 diffusers 实验 Notebook（`notebooks/`）

| 文件 | 内容 |
|------|------|
| `01.stable_diffusion开发.ipynb` | SD 1.5 文生图基础：管线加载、采样器、CFG、种子 |
| `02.图生图.ipynb` | img2img：`strength` 对结果的影响 |
| `03.sdxl随机生成.ipynb` | SDXL 双文本编码器 + 更大分辨率 |
| `04.civitai下载的Lora模型应用.ipynb` | 加载社区 LoRA 权重、触发词写法 |
| `05.高清修复.ipynb` | hires fix：低分辨率出图后放大重绘 |

### 二、2 个 Gradio 应用

| 文件 | 功能 |
|------|------|
| `server.py` | 文生图：中文 → LLM 扩写英文提示词 → SDXL 出图，可调推理步数与是否随机种子 |
| `server_img2img.py` | 图生图：在文生图基础上加入参考图与重绘强度 |

## 运行

```powershell
pip install -r requirements.txt

# 模型放到项目下的 models/stable-diffusion-xl-base-1.0/
# 或用环境变量指定任意位置
$env:SDXL_DIR = "D:\models\stable-diffusion-xl-base-1.0"
$env:SENSENOVA_API_KEY = "你的 Key"

python server.py            # http://127.0.0.1:7861
python server_img2img.py
```

## 实现要点

- **显存优化**：`torch_dtype=float16` + `enable_model_cpu_offload()` + 关闭安全检查器，6GB 显存实测峰值约 5.2GB。
- **全局单例**：模型只加载一次并全局复用，避免每次点按钮都重新读权重。
- **提示词容错**：LLM 调用最多重试 3 次；全部失败时退化为「中文原文 + 质量词」，保证永远能出图。
- **`server_img2img.pyi`** 属于 IDE 补全用的类型存根，已从仓库剔除，保留可运行的 `.py`。
