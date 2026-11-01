# -*- coding: utf-8 -*-
"""
test.py —— AI 绘画工作台（商汤付费绘画 API 版，无需本地模型和 GPU）
====================================================================
绘画模型：sensenova-u1.5-lite（OpenAI 兼容 /v1/images/generations 端点）

三个功能版块（与 server_img2img.py 对应，但生成走云端付费 API）：
    1. 🖌️ 文生图   —— 中文描述 → 商汤翻译 → API 生图
    2. 🖼️ 图生图   —— 上传图片 + 中文提示词 → API 重绘
    3. ✏️ 画板生成 —— 画板草稿 + 中文提示词 → API 上色

与本地 SDXL 版的参数差异：
    - steps / guidance_scale 是扩散采样参数，云端绘画 API 不接受 → 移除
    - API 真实参数：size（尺寸）、n（生成张数）→ 换成这些控件
    - strength（重绘幅度）→ 转译为提示词措辞传给绘画模型（轻改/中改/重构）

启动方式（复用 15-transformers-basics 的虚拟环境）：
    .\.venv\Scripts\Activate.ps1      # 先激活你自己的虚拟环境
    python test.py
    启动后浏览器打开 http://127.0.0.1:7863
"""

import os
import base64
import io
import socket
import threading
import traceback

import gradio as gr
import numpy as np
import requests
from langchain_openai import ChatOpenAI
from PIL import Image

API_BASE = 'https://token.sensenova.cn/v1'
API_KEY = os.getenv("SENSENOVA_API_KEY", "")
IMG_MODEL = 'sensenova-u1.5-lite'
SIZE_CHOICES = ['1024x1024', '1344x768', '768x1344']   # 方形 / 横版 / 竖版

# ============================================================
# 1. 商汤大模型：中文 → 英文提示词（翻译沿用项目配置）
# ============================================================
llm = ChatOpenAI(
    model='sensenova-6.8-flash-lite',
    base_url=API_BASE,
    temperature=0.6,
    # 不要设 max_tokens：商汤 6.8 是推理模型，思考也计入 token，限额会掏空正文
    api_key=API_KEY,
)

TRANSLATE_SYS = (
    '你是专业绘画提示词专家。把用户的中文描述扩写成一段详细的绘画指令：'
    '保留原意，补充画面细节（主体外观、动作、环境、光照、构图、艺术风格）。'
    '总长度控制在 120 个汉字或 60 个英文单词以内。'
    '只输出扩写后的提示词，不要解释、不要引号。'
)


def translate_prompt(cn_text: str) -> str:
    """中文描述 → 绘画提示词（sensenova-u1.5 支持中文，但扩写后更稳；失败退回原文）"""
    cn_text = (cn_text or '').strip()
    if not cn_text:
        return ''
    try:
        for _ in range(3):
            resp = llm.invoke([
                {'role': 'system', 'content': TRANSLATE_SYS},
                {'role': 'user', 'content': cn_text},
            ])
            out = resp.content.strip().strip('"')
            if out and len(out) > 3:
                return out
        return cn_text
    except Exception as e:
        print(f'⚠️ 提示词扩写失败（{e}），使用原始输入')
        return cn_text


# ============================================================
# 2. 绘画 API 封装（文生图 / 图生图同一个端点，image 字段可选）
# ============================================================
lock = threading.Lock()   # 串行调用，避免并发请求重复计费/限流


def _img_to_data_url(image: Image.Image) -> str:
    """PIL 图 → data URL（JPEG base64），作为图生图的参考图"""
    buf = io.BytesIO()
    image.convert('RGB').save(buf, 'JPEG', quality=90)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def call_image_api(prompt, size='1024x1024', n=1, image=None):
    """调用 sensenova-u1.5-lite 生图：传 image 即图生图，不传即文生图"""
    payload = {'model': IMG_MODEL, 'prompt': prompt, 'n': int(n), 'size': size}
    if image is not None:
        payload['image'] = _img_to_data_url(image)

    r = requests.post(
        f'{API_BASE}/images/generations',
        headers={'Authorization': f'Bearer {API_KEY}'},
        json=payload, timeout=300,
    )
    r.raise_for_status()
    images = []
    for item in r.json().get('data', []):
        if item.get('b64_json'):
            raw = base64.b64decode(item['b64_json'])
        elif item.get('url'):
            raw = requests.get(item['url'], timeout=60).content
        else:
            continue
        images.append(Image.open(io.BytesIO(raw)).convert('RGB'))
    return images


def strength_word(s: float) -> str:
    """重绘幅度滑块 → 提示词措辞（API 无 strength 参数，用语义控制改动程度）"""
    if s < 0.45:
        return '轻度调整：保持原图的主体、构图基本不变，只做细节和质感修饰'
    if s < 0.7:
        return '中等幅度改动：保留原图主要构图和主体特征，风格与背景可明显变化'
    return '大幅重构：把原图仅作为构图参考，充分按提示词重新创作画面'


# ============================================================
# 3. 三个版块的生成函数
# ============================================================
def _pick_images(prompt, size, n, image=None, strength=None):
    """公共流程：可选地融入重绘幅度 → 调 API → 返回 (第一张图, 状态, 提示词)"""
    if strength is not None:
        prompt = f'（改动要求：{strength_word(strength)}）{prompt}'
    with lock:
        images = call_image_api(prompt, size=size, n=n, image=image)
    return images[0], images, prompt


def generate_t2i(cn_text, size, n, progress=gr.Progress()):
    cn_text = (cn_text or '').strip()
    if not cn_text:
        return None, '请先输入中文画面描述', ''
    progress(0.2, desc='商汤模型扩写提示词…')
    prompt = translate_prompt(cn_text)
    progress(0.4, desc=f'云端绘画中（{IMG_MODEL}，约 10~30 秒）…')
    image, _, final_prompt = _pick_images(prompt, size, n)
    return image, f'✅ 文生图完成 | {size} | {n} 张', final_prompt


def generate_i2i(init_image, cn_text, size, n, strength, progress=gr.Progress()):
    if init_image is None:
        return None, '请先上传一张图片', ''
    cn_text = (cn_text or '').strip()
    if not cn_text:
        return None, '请先输入中文提示词（想改成什么样）', ''
    progress(0.2, desc='商汤模型扩写提示词…')
    prompt = translate_prompt(cn_text)
    progress(0.4, desc=f'云端重绘中（{IMG_MODEL}，约 10~30 秒）…')
    image, _, final_prompt = _pick_images(prompt, size, n, image=init_image, strength=strength)
    return image, f'✅ 图生图完成 | {size} | 幅度 {strength}', final_prompt


class SafeSketchpad(gr.Sketchpad):
    """gradio 6.27 Sketchpad 的防御性子类（与 server_img2img.py 相同方案）。

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
                img = Image.open(io.BytesIO(raw))
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


def generate_sketch(sketch, cn_text, size, n, strength, progress=gr.Progress()):
    canvas = extract_canvas(sketch)
    if canvas is None or not getattr(canvas, 'getbbox', lambda: None)():
        return None, '请先在画板上画点什么（建议白底黑笔简笔画）', ''
    cn_text = (cn_text or '').strip()
    if not cn_text:
        return None, '请先输入中文提示词（想让画变成什么）', ''
    progress(0.2, desc='商汤模型扩写提示词…')
    prompt = translate_prompt(cn_text)
    progress(0.4, desc=f'云端上色中（{IMG_MODEL}，约 10~30 秒）…')
    image, _, final_prompt = _pick_images(prompt, size, n, image=canvas, strength=strength)
    return image, f'✅ 画板生成完成 | {size} | 幅度 {strength}', final_prompt


# ============================================================
# 4. 页面
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

with gr.Blocks(title='AI 绘画工作台（商汤 API 版）') as demo:
    gr.Markdown('# 🎨 AI 绘画工作台 · 商汤绘画 API', elem_classes=['main-title'])
    gr.Markdown('<p class="footer-note">中文输入 → 商汤大模型扩写提示词 → sensenova-u1.5-lite 云端生图（无需本地模型/GPU）</p>')

    with gr.Tabs():
        # ---------------- Tab 1：文生图 ----------------
        with gr.Tab('🖌️ 文生图'):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown('### 📝 输入')
                    cn_t2i = gr.Textbox(
                        label='中文画面描述', lines=3,
                        placeholder='例如：一只戴宇航员头盔的橘猫漂浮在太空中，背景是蓝色地球',
                    )
                    size_t2i = gr.Radio(SIZE_CHOICES, value='1024x1024', label='图片尺寸')
                    n_t2i = gr.Slider(1, 4, value=1, step=1, label='生成张数（每张都计费）')
                    btn_t2i = gr.Button('🖼️ 生成图片', variant='primary')

                with gr.Column(scale=1):
                    gr.Markdown('### 🖼️ 输出')
                    img_t2i = gr.Image(label='生成结果', height=460)
                    info_t2i = gr.Textbox(label='状态', interactive=False)
                    prompt_t2i = gr.Textbox(label='扩写后的提示词', interactive=False, lines=3)

            btn_t2i.click(generate_t2i, inputs=[cn_t2i, size_t2i, n_t2i],
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
                                             label='重绘幅度（转译为改动措辞：小=细节修饰 / 大=重新创作）')
                    size_i2i = gr.Radio(SIZE_CHOICES, value='1024x1024', label='输出尺寸')
                    n_i2i = gr.Slider(1, 4, value=1, step=1, label='生成张数（每张都计费）')
                    btn_i2i = gr.Button('🔄 开始重绘', variant='primary')

                with gr.Column(scale=1):
                    gr.Markdown('### 🖼️ 输出')
                    img_i2i = gr.Image(label='重绘结果', height=460)
                    info_i2i = gr.Textbox(label='状态', interactive=False)
                    prompt_i2i = gr.Textbox(label='扩写后的提示词', interactive=False, lines=3)

            btn_i2i.click(generate_i2i,
                          inputs=[init_img, cn_i2i, size_i2i, n_i2i, strength_i2i],
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
                        canvas_size=(1024, 1024),
                        buttons=['fullscreen', 'download'],
                    )
                    cn_sk = gr.Textbox(
                        label='中文提示词（想让画变成什么）', lines=2,
                        placeholder='例如：一只在草地上的柴犬，吉卜力风格，蓝天白云',
                    )
                    strength_sk = gr.Slider(0.2, 0.9, value=0.7, step=0.05,
                                            label='重绘幅度（转译为改动措辞：小=贴草稿 / 大=自由发挥）')
                    size_sk = gr.Radio(SIZE_CHOICES, value='1024x1024', label='输出尺寸')
                    n_sk = gr.Slider(1, 4, value=1, step=1, label='生成张数（每张都计费）')
                    btn_sk = gr.Button('✨ AI 上色', variant='primary')

                with gr.Column(scale=1):
                    gr.Markdown('### 🖼️ 输出')
                    img_sk = gr.Image(label='AI 上色结果', height=460)
                    info_sk = gr.Textbox(label='状态', interactive=False)
                    prompt_sk = gr.Textbox(label='扩写后的提示词', interactive=False, lines=3)

            btn_sk.click(generate_sketch,
                         inputs=[sketch, cn_sk, size_sk, n_sk, strength_sk],
                         outputs=[img_sk, info_sk, prompt_sk])

    gr.Markdown('<p class="footer-note">绘画模型：sensenova-u1.5-lite（商汤云端 API，按张计费）· 提示词扩写：sensenova-6.8-flash-lite</p>')


def port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


if __name__ == '__main__':
    HOST, PORT = '127.0.0.1', 7863   # 7860/7861/7862 已被其他课程服务占用

    if port_in_use(HOST, PORT):
        print(f'⚠️ 端口 {PORT} 已被占用：服务可能已经在运行了。')
        print(f'   请直接用浏览器打开 http://{HOST}:{PORT} ；')
        print(f'   如需重启，请先在原来运行的窗口按 Ctrl+C 结束旧服务。')
        raise SystemExit(0)

    print('⏳ 正在启动 AI 绘画工作台（商汤 API 版，无需加载本地模型）……', flush=True)
    print(f'✅ 启动成功后：浏览器访问 http://{HOST}:{PORT} ；停止请按 Ctrl+C', flush=True)
    # Gradio 6：theme/css 必须传给 launch()，写进 Blocks 构造函数会报警告
    demo.launch(server_name=HOST, server_port=PORT, inbrowser=True,
                theme=theme, css=CSS,
                max_threads=1, show_error=True)
