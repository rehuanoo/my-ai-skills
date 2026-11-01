# -*- coding: utf-8 -*-
"""
AI 绘画工作台 Pro —— Gradio 三合一绘画应用
==========================================
三个功能版块（Tabs）：
    1. 🖌️ 文生图   —— 中文描述 → 商汤翻译 → SDXL 生成
    2. 🖼️ 图生图   —— 上传图片 + 中文提示词 → 商汤翻译 → SDXL 重绘
    3. ✏️ 画板生成 —— 用户在画板上画草稿 + 中文提示词 → SDXL 上色成图

用户可调参数：重绘幅度（strength）、指导比例（guidance_scale）、
             推理步数（steps）、随机/固定种子（seed）

启动方式（复用 15-transformers-basics 的虚拟环境）：
    .\.venv\Scripts\Activate.ps1      # 先激活你自己的虚拟环境
    python server_img2img.py
    启动后浏览器打开 http://127.0.0.1:7862
"""

import os
import socket
import threading
import traceback
from io import BytesIO

import gradio as gr
import numpy as np
import torch
from langchain_openai import ChatOpenAI
from PIL import Image

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
    cn_text = (cn_text or '').strip()
    if not cn_text:
        return ''
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
# 2. 本地 SDXL：文生图 + 图生图两条管线，共享同一套模型组件
#    （SDXL 权重 6.9GB，独立加载两份会占双倍内存；用 pipe.components
#     把组件直接传给 Img2ImgPipeline，两个管线共用同一批权重）
# ============================================================
pipe_t2i = None     # StableDiffusionXLPipeline（文生图）
pipe_i2i = None     # StableDiffusionXLImg2ImgPipeline（图生图/画板）
lock = threading.Lock()   # 模型非线程安全，全局加锁避免并发崩溃


def load_model():
    """惰性加载：首次生成时初始化（约 1 分钟），之后全局复用"""
    global pipe_t2i, pipe_i2i
    if pipe_t2i is not None:
        return
    from diffusers import StableDiffusionXLImg2ImgPipeline, StableDiffusionXLPipeline

    pipe_t2i = StableDiffusionXLPipeline.from_pretrained(
        SDXL_DIR, dtype=torch.float16, variant='fp16',
    )
    pipe_t2i.enable_model_cpu_offload()   # 8GB 显存装不下 6.9GB 权重：组件按需进出 GPU
    # VAE fp16 溢出（黑图）由 pipeline 依据 vae config 的 force_upcast 自动处理

    # 图生图管线：共享文生图的全部组件（显存/内存零额外开销）
    pipe_i2i = StableDiffusionXLImg2ImgPipeline(
        **pipe_t2i.components, requires_aesthetics_score=False,
    )
    print('✅ SDXL 双管线加载完成（共享组件）')


# ============================================================
# 3. 生成核心
# ============================================================
def _pick_seed(is_random, seed):
    """随机 = 每次不同；固定 = 使用输入值（可复现同一张图）"""
    if is_random:
        return torch.randint(0, 2**31 - 1, (1,)).item()
    return int(seed or 0)


def _run_t2i(en_prompt, steps, guidance, used_seed):
    return pipe_t2i(
        prompt=en_prompt,
        negative_prompt=DEFAULT_NEG,
        num_inference_steps=int(steps),
        guidance_scale=float(guidance),
        height=1024, width=1024,
        generator=torch.Generator('cuda').manual_seed(used_seed),
    ).images[0]


def _run_i2i(init_image, en_prompt, strength, steps, guidance, used_seed):
    if init_image.mode != 'RGB':
        init_image = init_image.convert('RGB')
    return pipe_i2i(
        prompt=en_prompt,
        negative_prompt=DEFAULT_NEG,
        image=init_image.resize((1024, 1024)),
        strength=float(strength),          # 重绘幅度：越大离原图越远
        num_inference_steps=int(steps),
        guidance_scale=float(guidance),
        generator=torch.Generator('cuda').manual_seed(used_seed),
    ).images[0]


def _tag(seed, is_random):
    return f'seed = {seed}' + ('（随机）' if is_random else '（固定）')


# ---------- 文生图 ----------
def generate_t2i(cn_text, steps, guidance, is_random, seed, progress=gr.Progress()):
    en_prompt = translate_prompt(cn_text)
    if not en_prompt:
        return None, '请先输入中文画面描述', ''
    used_seed = _pick_seed(is_random, seed)

    progress(0.1, desc='加载 SDXL 模型（首次约 1 分钟）…')
    with lock:
        load_model()
        progress(0.4, desc=f'SDXL 生成中（{steps} 步）…')
        image = _run_t2i(en_prompt, steps, guidance, used_seed)

    return image, f'✅ 文生图完成 | {_tag(used_seed, is_random)}', en_prompt


# ---------- 图生图 ----------
def generate_i2i(init_image, cn_text, strength, steps, guidance, is_random, seed,
                 progress=gr.Progress()):
    if init_image is None:
        return None, '请先上传一张图片', ''
    en_prompt = translate_prompt(cn_text)
    if not en_prompt:
        return None, '请先输入中文提示词（想把它改成什么样）', ''
    used_seed = _pick_seed(is_random, seed)

    progress(0.1, desc='加载 SDXL 模型（首次约 1 分钟）…')
    with lock:
        load_model()
        progress(0.4, desc=f'SDXL 重绘中（{steps} 步，幅度 {strength}）…')
        image = _run_i2i(init_image, en_prompt, strength, steps, guidance, used_seed)

    return image, f'✅ 图生图完成 | {_tag(used_seed, is_random)}', en_prompt


# ---------- 画板生成 ----------
class SafeSketchpad(gr.Sketchpad):
    """gradio 6.27 Sketchpad 的防御性子类。

    默认 preprocess 依赖前端 blob 上传（blob_storage），一旦字节流解析失败
    就会抛 ComponentProcessingError 导致"点击生成直接报错"。
    这里兜底：默认流程失败时手动从 blob_storage / payload 提取合成图，
    并把原始 traceback 打到服务端控制台，方便定位根因。
    （必须重写 get_block_name 返回 'imageeditor'，否则前端按子类类名找
    svelte 模板会找不到组件。）
    """

    def get_block_name(self) -> str:
        return 'imageeditor'

    def preprocess(self, payload):
        try:
            return super().preprocess(payload)
        except Exception:
            print('⚠️ Sketchpad 默认 preprocess 失败，启用兜底提取，原始异常：')
            traceback.print_exc()
            return self._manual_extract(payload)

    def _manual_extract(self, payload):
        """手动从 blob_storage（bytes）或 payload（FileData.path）提取 composite"""
        empty = {'background': None, 'layers': [], 'composite': None}
        try:
            if payload is None:
                return None
            raw = None                                   # bytes 或 FileData
            blob_id = getattr(payload, 'id', None)
            if blob_id:
                cached = self.blob_storage.get(blob_id)  # EditorDataBlobs
                if cached is not None:
                    raw = cached.composite if cached.composite is not None else cached.background
            if raw is None and getattr(payload, 'composite', None) is not None:
                raw = payload.composite
            if raw is None and getattr(payload, 'background', None) is not None:
                raw = payload.background
            if raw is None:
                return empty
            if isinstance(raw, (bytes, bytearray, memoryview)):
                img = Image.open(BytesIO(raw))
            else:                                        # FileData：本地缓存文件路径
                img = Image.open(raw.path)
            img = img.convert('RGBA')
            if self.type == 'numpy':                     # 与组件 type 参数保持一致
                img = np.array(img)
            # 注意：不 pop blob_storage，用户重试仍可取到
            return {'background': None, 'layers': [], 'composite': img}
        except Exception:
            print('⚠️ Sketchpad 兜底提取也失败，按空画布处理：')
            traceback.print_exc()
            return empty


def extract_canvas(value):
    """兼容 Sketchpad 各种返回形态（dict / PIL / ndarray / 文件路径），统一提取为 PIL 图"""
    if value is None:
        return None
    if isinstance(value, dict):
        img = value.get('composite')          # 不能用 or：ndarray 的真值有歧义
        if img is None:
            img = value.get('background')
    elif isinstance(value, str):
        img = Image.open(value)
    else:
        img = value
    if img is None:
        return None
    if isinstance(img, np.ndarray):           # type='numpy'（默认）时 gradio 返回 ndarray
        img = Image.fromarray(img)
    if not isinstance(img, Image.Image):
        return None
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    return img


def generate_sketch(sketch, cn_text, strength, steps, guidance, is_random, seed,
                    progress=gr.Progress()):
    canvas = extract_canvas(sketch)
    if canvas is None or not getattr(canvas, 'getbbox', lambda: None)():
        return None, '请先在画板上画点什么（建议白底黑笔简笔画）', ''
    en_prompt = translate_prompt(cn_text)
    if not en_prompt:
        return None, '请先输入中文提示词（想让画变成什么风格/内容）', ''
    used_seed = _pick_seed(is_random, seed)

    progress(0.1, desc='加载 SDXL 模型（首次约 1 分钟）…')
    with lock:
        load_model()
        progress(0.4, desc=f'SDXL 上色中（{steps} 步，幅度 {strength}）…')
        image = _run_i2i(canvas, en_prompt, strength, steps, guidance, used_seed)

    return image, f'✅ 画板生成完成 | {_tag(used_seed, is_random)}', en_prompt


# ============================================================
# 4. 页面（Soft 主题 + 自定义 CSS）
# ============================================================
CSS = '''
.main-title {
  text-align: center;
  background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 800;
}
.footer-note { text-align: center; color: #9ca3af; font-size: 12px; }
'''

theme = gr.themes.Soft(
    primary_hue='indigo', secondary_hue='purple', neutral_hue='slate',
).set(body_background_fill='*neutral_50')

with gr.Blocks(title='AI 绘画工作台 Pro') as demo:
    gr.Markdown('# 🎨 AI 绘画工作台 Pro', elem_classes=['main-title'])
    gr.Markdown('<p class="footer-note">中文输入 → 商汤大模型翻译提示词 → 本地 SDXL 生图</p>')

    with gr.Tabs():
        # ---------------- Tab 1：文生图 ----------------
        with gr.Tab('🖌️ 文生图'):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown('### 📝 输入')
                    cn_t2i = gr.Textbox(
                        label='中文画面描述', lines=3, placeholder='例如：一只戴宇航员头盔的橘猫漂浮在太空中，背景是蓝色地球',
                    )
                    steps_t2i = gr.Slider(15, 50, value=30, step=1, label='推理步数（越大越精细、越慢）')
                    guidance_t2i = gr.Slider(1.0, 12.0, value=5.0, step=0.5,
                                             label='指导比例 guidance_scale（越大越贴提示词）')
                    is_random_t2i = gr.Checkbox(value=True, label='随机种子（取消勾选可固定 seed 复现）')
                    seed_t2i = gr.Number(value=42, label='固定 seed', precision=0, visible=False)
                    btn_t2i = gr.Button('🖼️ 生成图片', variant='primary')

                with gr.Column(scale=1):
                    gr.Markdown('### 🖼️ 输出')
                    img_t2i = gr.Image(label='生成结果', height=460)
                    info_t2i = gr.Textbox(label='状态', interactive=False)
                    prompt_t2i = gr.Textbox(label='商汤翻译的英文提示词', interactive=False, lines=3)

            def toggle_t2i(use_random):
                return gr.update(visible=not use_random)

            is_random_t2i.change(toggle_t2i, inputs=is_random_t2i, outputs=seed_t2i)
            btn_t2i.click(generate_t2i, inputs=[cn_t2i, steps_t2i, guidance_t2i, is_random_t2i, seed_t2i],
                          outputs=[img_t2i, info_t2i, prompt_t2i])

        # ---------------- Tab 2：图生图 ----------------
        with gr.Tab('🖼️ 图生图'):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown('### 📤 上传原图 + 描述改动')
                    init_img = gr.Image(label='原图（上传后会被重绘）', type='pil', height=300)
                    cn_i2i = gr.Textbox(
                        label='中文提示词（想改成什么样）', lines=2,
                        placeholder='例如：把它变成油画风格，暖色调，背景换成夕阳海边',
                    )
                    strength_i2i = gr.Slider(0.2, 0.9, value=0.6, step=0.05,
                                             label='重绘幅度 strength（越大改动越大：0.3 微调 / 0.8 大改）')
                    steps_i2i = gr.Slider(15, 50, value=30, step=1, label='推理步数')
                    guidance_i2i = gr.Slider(1.0, 12.0, value=5.0, step=0.5, label='指导比例 guidance_scale')
                    is_random_i2i = gr.Checkbox(value=True, label='随机种子（取消勾选可固定 seed 复现）')
                    seed_i2i = gr.Number(value=42, label='固定 seed', precision=0, visible=False)
                    btn_i2i = gr.Button('🔄 开始重绘', variant='primary')

                with gr.Column(scale=1):
                    gr.Markdown('### 🖼️ 输出')
                    img_i2i = gr.Image(label='重绘结果', height=460)
                    info_i2i = gr.Textbox(label='状态', interactive=False)
                    prompt_i2i = gr.Textbox(label='商汤翻译的英文提示词', interactive=False, lines=3)

            def toggle_i2i(use_random):
                return gr.update(visible=not use_random)

            is_random_i2i.change(toggle_i2i, inputs=is_random_i2i, outputs=seed_i2i)
            btn_i2i.click(generate_i2i,
                          inputs=[init_img, cn_i2i, strength_i2i, steps_i2i, guidance_i2i,
                                  is_random_i2i, seed_i2i],
                          outputs=[img_i2i, info_i2i, prompt_i2i])

        # ---------------- Tab 3：画板生成 ----------------
        with gr.Tab('✏️ 画板生成'):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown('### ✏️ 画个草稿，AI 帮你上色')
                    sketch = SafeSketchpad(
                        label='画板（画简笔画草稿 · 点右上角 ⛶ 可全屏放大作画）',
                        height=560,
                        brush=gr.Brush(default_size=18, colors=['#111827']),
                        canvas_size=(1024, 1024),   # 与 SDXL 输出同分辨率，笔迹不糊
                        buttons=['fullscreen', 'download'],
                    )
                    cn_sk = gr.Textbox(
                        label='中文提示词（想让画变成什么）', lines=2,
                        placeholder='例如：一只在草地上的柴犬，吉卜力风格，蓝天白云',
                    )
                    strength_sk = gr.Slider(0.4, 0.95, value=0.8, step=0.05,
                                            label='重绘幅度 strength（画板建议 0.7~0.9：保构图、换质感）')
                    steps_sk = gr.Slider(15, 50, value=30, step=1, label='推理步数')
                    guidance_sk = gr.Slider(1.0, 12.0, value=5.0, step=0.5, label='指导比例 guidance_scale')
                    is_random_sk = gr.Checkbox(value=True, label='随机种子（取消勾选可固定 seed 复现）')
                    seed_sk = gr.Number(value=42, label='固定 seed', precision=0, visible=False)
                    btn_sk = gr.Button('✨ AI 上色', variant='primary')

                with gr.Column(scale=1):
                    gr.Markdown('### 🖼️ 输出')
                    img_sk = gr.Image(label='AI 上色结果', height=460)
                    info_sk = gr.Textbox(label='状态', interactive=False)
                    prompt_sk = gr.Textbox(label='商汤翻译的英文提示词', interactive=False, lines=3)

            def toggle_sk(use_random):
                return gr.update(visible=not use_random)

            is_random_sk.change(toggle_sk, inputs=is_random_sk, outputs=seed_sk)
            btn_sk.click(generate_sketch,
                         inputs=[sketch, cn_sk, strength_sk, steps_sk, guidance_sk,
                                 is_random_sk, seed_sk],
                         outputs=[img_sk, info_sk, prompt_sk])

    gr.Markdown('<p class="footer-note">模型：stable-diffusion-xl-base-1.0（本地）· 提示词翻译：商汤 SenseNova · '
                '显存优化 fp16 + CPU offload</p>')


def port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


if __name__ == '__main__':
    HOST, PORT = '127.0.0.1', 7862   # 7860/7861 已被其他课程服务占用

    if port_in_use(HOST, PORT):
        print(f'⚠️ 端口 {PORT} 已被占用：服务可能已经在运行了。')
        print(f'   请直接用浏览器打开 http://{HOST}:{PORT} ；')
        print(f'   如需重启，请先在原来运行的窗口按 Ctrl+C 结束旧服务。')
        raise SystemExit(0)

    print('⏳ 正在启动 AI 绘画工作台 Pro（首次生成时加载 SDXL 模型约 1 分钟）……', flush=True)
    print(f'✅ 启动成功后：浏览器访问 http://{HOST}:{PORT} ；停止请按 Ctrl+C', flush=True)
    # Gradio 6：theme/css 必须传给 launch()，写进 Blocks 构造函数会报警告
    demo.launch(server_name=HOST, server_port=PORT, inbrowser=True,
                theme=theme, css=CSS,
                max_threads=1, show_error=True)
