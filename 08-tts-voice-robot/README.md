# 08 · 智能语音机器人（Whisper + XTTS-v2 + LLM）

> 你说一句话，它用「别人的音色」回答你 —— 语音识别、大模型对话、音色克隆合成，三件事串成一个闭环。

## 技术栈

`coqui-tts (XTTS-v2)` · `OpenAI Whisper large-v3` · 商汤 SenseNova（OpenAI 兼容）· `Gradio` · `soundfile` / `librosa`

## 两个 Notebook

### `02.Coqui-TTS本地XTTS-v2中文声音克隆.ipynb`
- XTTS-v2 本地加载与中文推理
- **零样本音色克隆**：给一段 10 秒左右的参考音频，就能用这个音色说任意内容
- 参考音频的前处理（采样率、时长、静音裁剪）

### `03.智能语音机器人.ipynb`
完整流水线：

```
Gradio 录音 → Whisper large-v3 识别 → 组装最近 6 轮对话历史
          → 商汤 LLM 生成回复 → XTTS-v2 用克隆音色合成 → 播放
```

## 环境要求

```powershell
pip install -r requirements.txt
# 首次运行会自动下载 whisper-large-v3 与 XTTS-v2 权重（数 GB）
$env:SENSENOVA_API_KEY = "你的 Key"
```

> 参考音频（`*.wav`）已从仓库剔除，请自己准备一段 10 秒左右、无背景音乐的人声。

## 实现要点

- **兼容性补丁**：`coqui-tts 0.27.5` 与 `transformers 5.x` 存在 API 冲突，Notebook 第一个 Cell 就打了补丁，避免后面莫名报错。
- **条件向量预计算**：XTTS 的参考音色只需算一次，之后全程复用，省掉每次合成的重复开销。
- **预热**：Whisper 首次推理要初始化 CUDA kernel，用 0.5 秒空白音频先跑一次，用户第一次说话就不会卡顿。
- **TPM 限流重试**：商汤 API 约 5 次连续调用触发 429，做了指数退避重试。
- **历史控制**：只保留最近 6 轮对话，防止上下文无限膨胀拖慢合成。
