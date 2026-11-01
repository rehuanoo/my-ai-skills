# -*- coding: utf-8 -*-
"""
server.py —— AI 海报生成后端（Gradio）
====================================================================
流程：
    用户中文要求 → 商汤 6.8-flash-lite 撰写「海报词 JSON + 配图英文提示词」
    → 商汤 u1.5-lite 按提示词画一张竖版配图 → 一起返回

前端 vite-poster（App.vue）通过 @gradio/client 调用本服务的
/generate_poster 接口，拿到配图 + 海报词后用 Fabric 自动排版成海报。

启动（复用 15-transformers-basics 虚拟环境）：
    .\.venv\Scripts\Activate.ps1      # 先激活你自己的虚拟环境
    python server.py
    启动后：http://127.0.0.1:7864
"""

import os
import base64
import io
import json
import re
import socket
import threading

import gradio as gr
import requests
from PIL import Image

API_BASE = 'https://token.sensenova.cn/v1'
API_KEY = os.getenv("SENSENOVA_API_KEY", "")
LLM_MODEL = 'sensenova-6.8-flash-lite'   # 推理模型：不要设 max_tokens（思考计入额度会掏空正文）
IMG_MODEL = 'sensenova-u1.5-lite'
IMG_SIZE = '768x1344'   # 竖版，接近海报右侧配图区比例（438x780 ≈ 0.56）

lock = threading.Lock()   # 绘画 API 串行调用，避免限流

# ============================================================
# 1. 海报词生成（LLM 输出严格 JSON，前端按字段排版）
# ============================================================
COPY_SYS = (
    '你是金牌海报文案策划。根据用户要求为一张竖版体育风海报撰写文案，并给出配图绘画指令。'
    '只输出一个 JSON 对象，不要解释、不要代码围栏，字段如下：'
    '{'
    '"title": "主标题，2~6个汉字，通常是人物或主题名",'
    '"title_en": "英文副标题，全大写字母，10~20个字符，不要标点",'
    '"tagline": "一句标签语，6~14个汉字，中间可用 · 分隔",'
    '"points": [ {"label": "小分类，4~10个汉字", "value": "核心亮点，2~8个字"}, '
    '{"label": "...", "value": "..."}, {"label": "...", "value": "..."} ]，恰好3个'
    '"footer": "页脚备注，10~20个汉字，包含时间或出处",'
    '"image_prompt": "配图英文绘画提示词，60个英文单词以内：竖版构图，描述主体动作、'
    '场景氛围、光效与艺术风格（体育摄影/电影感/舞台泛光）。画面中不要出现任何文字、字母、水印"'
    '}'
)


def _chat(messages):
    r = requests.post(
        f'{API_BASE}/chat/completions',
        headers={'Authorization': f'Bearer {API_KEY}'},
        json={'model': LLM_MODEL, 'messages': messages, 'temperature': 0.8},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content'].strip()


def _parse_json(text):
    """剥掉 ```json 围栏后解析"""
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    return json.loads(text)


def _gen_copy(cn_req):
    """生成海报词，失败重试 3 次"""
    last_err = None
    for _ in range(3):
        try:
            data = _parse_json(_chat([
                {'role': 'system', 'content': COPY_SYS},
                {'role': 'user', 'content': cn_req},
            ]))
            assert isinstance(data.get('title'), str) and data['title'].strip(), '缺少 title'
            assert isinstance(data.get('image_prompt'), str) and data['image_prompt'].strip(), '缺少 image_prompt'
            data.setdefault('title_en', '')
            data.setdefault('tagline', '')
            data.setdefault('footer', '')
            # 成就点：最多 3 个，每个只留 label/value/sub
            points = []
            for p in data.get('points', []):
                if isinstance(p, dict) and p.get('label') and p.get('value'):
                    points.append({'label': str(p['label']), 'value': str(p['value']),
                                   'sub': str(p.get('sub', ''))})
            data['points'] = points[:3]
            return data
        except Exception as e:
            last_err = e
    raise gr.Error(f'海报词生成失败：{last_err}')


# ============================================================
# 2. 配图生成（文生图端点，竖版）
# ============================================================
def _call_image_api(prompt):
    r = requests.post(
        f'{API_BASE}/images/generations',
        headers={'Authorization': f'Bearer {API_KEY}'},
        json={'model': IMG_MODEL, 'prompt': prompt, 'n': 1, 'size': IMG_SIZE},
        timeout=300,
    )
    r.raise_for_status()
    item = r.json()['data'][0]
    if item.get('b64_json'):
        raw = base64.b64decode(item['b64_json'])
    else:
        raw = requests.get(item['url'], timeout=60).content
    return Image.open(io.BytesIO(raw)).convert('RGB')


# ============================================================
# 3. 对外接口：一次返回（配图, 海报词 JSON 字符串）
# ============================================================
def generate_poster(cn_req, progress=gr.Progress()):
    cn_req = (cn_req or '').strip()
    if not cn_req:
        raise gr.Error('请先输入海报要求（例如：给王楚钦做一张世乒赛夺冠海报，突出左手横拍）')
    progress(0.15, desc='商汤大模型撰写海报词…')
    copy = _gen_copy(cn_req)
    progress(0.5, desc=f'绘画模型生成竖版配图（{IMG_MODEL}，约 15~40 秒）…')
    with lock:
        img = _call_image_api(copy['image_prompt'])
    progress(1.0, desc='完成')
    return img, json.dumps(copy, ensure_ascii=False, indent=2)


with gr.Blocks(title='AI 海报生成后端') as demo:
    gr.Markdown(
        '# 🖼️ AI 海报生成后端\n'
        '中文要求 → 商汤 LLM 撰写海报词(JSON) + u1.5-lite 生成竖版配图。\n\n'
        '前端 vite-poster 通过 @gradio/client 调用 `/generate_poster` 接口。'
    )
    cn = gr.Textbox(
        label='海报要求', lines=3,
        placeholder='例如：给王楚钦做一张世乒赛夺冠海报，突出左手横拍和世界第一',
    )
    btn = gr.Button('🚀 生成海报素材', variant='primary')
    img = gr.Image(label='竖版配图', type='pil', height=420)
    js = gr.Textbox(label='海报词 JSON（title / title_en / tagline / points / footer）',
                    lines=10, interactive=False)
    btn.click(generate_poster, inputs=cn, outputs=[img, js], api_name='generate_poster')


def port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


if __name__ == '__main__':
    HOST, PORT = '127.0.0.1', 7864   # 7860~7863 已被其他课程服务占用

    if port_in_use(HOST, PORT):
        print(f'⚠️ 端口 {PORT} 已被占用：服务可能已在运行，直接浏览器打开 http://{HOST}:{PORT}')
        raise SystemExit(0)

    print('⏳ 正在启动 AI 海报后端（无需本地模型，全部走商汤云端 API）……', flush=True)
    print(f'✅ 启动后：http://{HOST}:{PORT} ；停止请按 Ctrl+C', flush=True)
    demo.launch(server_name=HOST, server_port=PORT, max_threads=1, show_error=True)
