# -*- coding: utf-8 -*-
"""
AI 绘画工作台 —— Gradio 文生图应用
==================================
流程：用户输入中文描述 → 商汤付费大模型翻译/扩写成英文提示词
     → 本地 SDXL 模型（stable-diffusion-xl-base-1.0）生成图片

前端可控制：
    - 推理步数（滑块，15~50）
    - 是否随机种子（勾选 = 每次出新图；不勾选 = 固定 seed 可复现）

启动方式（复用 15-transformers-basics 的虚拟环境）：
    .\.venv\Scripts\Activate.ps1      # 先激活你自己的虚拟环境
    python server.py
    启动后浏览器打开 http://127.0.0.1:7861
"""

import os
import socket
import threading

import gradio as gr
import torch
from langchain_openai import ChatOpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SDXL_DIR = os.getenv('SDXL_DIR',
                     os.path.join(BASE_DIR, 'models', 'stable-diffusion-xl-base-1.0'))
DEFAULT_NEG = 'lowres, bad anatomy, bad hands, blurry, watermark, text'

# ============================================================
# 1. 商汤大模型：中文 → 英文提示词（复用课程项目的配置）
# ============================================================
llm = ChatOpenAI(
    model='sensenova-6.8-flash-lite',
    base_url='https://token.sensenova.cn/v1',
    temperature=0.6,
    # 注意：不要设 max_tokens——商汤 6.8 是推理模型，思考过程也计入 token，
    # 限额太低会把思考用完，正文 content 为空
    api_key=os.getenv("SENSENOVA_API_KEY", ""),
)

TRANSLATE_SYS = (
    '你是 Stable Diffusion 提示词专家。把用户的中文描述翻译并扩写成一段英文绘画提示词：'
    '保留原意，补充画面细节（主体外观、动作、环境、光照、构图）和质量词（highly detailed, sharp focus 等）。'
    '总长度控制在 55 个英文单词以内（SDXL 文本编码器上限 77 token，超长会被截断）。'
    '只输出英文提示词本身，不要解释、不要引号、不要换行。'
)


def translate_prompt(cn_text: str) -> str:
    """中文描述 → 英文 SD 提示词（失败时退化为简单拼接，保证能出图）"""
    try:
        for _ in range(3):  # 重试 3 次
            resp = llm.invoke([
                {'role': 'system', 'content': TRANSLATE_SYS},
                {'role': 'user', 'content': cn_text},
            ])
            en = resp.content.strip().strip('"')
            if en and len(en) > 5:
                return en
        return cn_text + ', highly detailed, sharp focus'
    except Exception as e:
        print(f'⚠️ 提示词翻译失败（{e}），使用原始输入拼接')
        return cn_text + ', highly detailed, sharp focus'


# ============================================================
# 2. 本地 SDXL：加载一次全局复用（fp16 + CPU offload，8GB 显存实测 5.2GB）
# ============================================================
pipe = None
lock = threading.Lock()   # 生成函数全局加锁：模型非线程安全，避免并发崩溃


def load_model():
    global pipe
    if pipe is not None:
        return
    from diffusers import StableDiffusionXLPipeline

    pipe = StableDiffusionXLPipeline.from_pretrained(
        SDXL_DIR, dtype=torch.float16, variant='fp16',
    )
    pipe.enable_model_cpu_offload()   # 6.9GB 权重装不下 8GB 显存：组件按需进出 GPU
    # VAE fp16 溢出（黑图）由 pipeline 依据 vae config 的 force_upcast 自动处理
    print('✅ SDXL 模型加载完成')


# ============================================================
# 3. 生成函数：翻译 → 生图
# ============================================================
def generate(cn_text, steps, is_random, seed, progress=gr.Progress()):
    cn_text = (cn_text or '').strip()
    if not cn_text:
        return None, '请先输入中文画面描述', ''

    progress(0.05, desc='调用商汤模型翻译提示词…')
    en_prompt = translate_prompt(cn_text)

    # 种子：随机 = 每次不同；固定 = 使用输入值（可复现同一张图）
    used_seed = torch.randint(0, 2**31 - 1, (1,)).item() if is_random else int(seed)

    progress(0.2, desc='加载 SDXL 模型（首次约 1 分钟）…')
    with lock:
        load_model()
        progress(0.4, desc=f'SDXL 生成中（{steps} 步，约 1 分钟）…')
        image = pipe(
            prompt=en_prompt,
            negative_prompt=DEFAULT_NEG,
            num_inference_steps=int(steps),
            guidance_scale=5.0,
            height=1024, width=1024,
            generator=torch.Generator('cuda').manual_seed(used_seed),
        ).images[0]

    info = f'✅ 生成完成 | seed = {used_seed}' + ('（随机）' if is_random else '（固定）')
    return image, info, en_prompt


# ============================================================
# 4. 页面
# ============================================================
with gr.Blocks(title='AI 绘画工作台') as demo:
    gr.Markdown('# 🎨 AI 绘画工作台（中文输入 → 商汤翻译 → SDXL 生图）')

    with gr.Row():
        with gr.Column(scale=1):
            cn_input = gr.Textbox(
                label='中文画面描述', lines=3,
                placeholder='例如：一只戴宇航员头盔的橘猫漂浮在太空中，背景是蓝色地球',
            )
            steps = gr.Slider(15, 50, value=30, step=1,
                              label='推理步数（越大越精细、越慢）')
            is_random = gr.Checkbox(value=True, label='随机种子（取消勾选可固定 seed 复现）')
            seed = gr.Number(value=42, label='固定 seed', precision=0, visible=False)
            btn = gr.Button('🖼️ 生成图片', variant='primary')

        with gr.Column(scale=1):
            out_img = gr.Image(label='生成结果', height=500)
            out_info = gr.Textbox(label='状态', interactive=False)
            out_prompt = gr.Textbox(label='商汤翻译的英文提示词', interactive=False, lines=3)

    # 是否随机 → 控制固定 seed 输入框的显示/隐藏
    def toggle_seed(use_random):
        return gr.update(visible=not use_random)

    is_random.change(toggle_seed, inputs=is_random, outputs=seed)
    btn.click(generate, inputs=[cn_input, steps, is_random, seed],
              outputs=[out_img, out_info, out_prompt])


def port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


if __name__ == '__main__':
    HOST, PORT = '127.0.0.1', 7861   # 7860 已被 01-llm-knowledge-workspace 工作台占用

    if port_in_use(HOST, PORT):
        print(f'⚠️ 端口 {PORT} 已被占用：服务可能已经在运行了。')
        print(f'   请直接用浏览器打开 http://{HOST}:{PORT} ；')
        print(f'   如需重启，请先在原来运行 server.py 的窗口按 Ctrl+C 结束旧服务。')
        raise SystemExit(0)

    print('⏳ 正在启动 AI 绘画工作台（首次生成时加载 SDXL 模型约 1 分钟）……', flush=True)
    print(f'✅ 启动成功后：浏览器访问 http://{HOST}:{PORT} ；停止请按 Ctrl+C', flush=True)
    demo.launch(server_name=HOST, server_port=PORT, inbrowser=True,
                max_threads=1, show_error=True)
