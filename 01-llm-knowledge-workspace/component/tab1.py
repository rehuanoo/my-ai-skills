# -*- coding: utf-8 -*-
"""
Tab 1：数学知识点扩充工作台
==========================
从 07-langchain-rag/txt/math 的可视化 HTML 页面自动生成知识点 Markdown 文档。

操作三步（三个按钮）：
    ① 读取 HTML 文件 —— 查看选中页面的原始 HTML
    ② 提取关键内容   —— BeautifulSoup 解析 <meta> 元数据和页面文字
    ③ 生成知识点     —— 调用商汤 SenseNova 付费模型生成文档并保存

对外只暴露 create_tab()，由 server.py 挂载到主页面。
"""

import os
import glob
import time

import gradio as gr
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI

# ============================================================
# 路径与模型配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 项目根目录
MATH_DIR = os.path.join(BASE_DIR, 'sample_docs', 'math')          # 44 个可视化 HTML
OUT_DIR = os.path.join(BASE_DIR, 'knowledge_docs')    # 生成的知识点文档
os.makedirs(OUT_DIR, exist_ok=True)

# 付费大模型（商汤 SenseNova，OpenAI 兼容协议）
llm = ChatOpenAI(
    model='sensenova-6.8-flash-lite',
    base_url='https://token.sensenova.cn/v1',
    api_key=os.getenv("SENSENOVA_API_KEY", ""),
    temperature=0.4,
    timeout=120,
)

# 知识点文档生成提示词（与 07-langchain-rag/10.扩充知识库.ipynb 一致）
DOC_PROMPT = '''你是数学老师。请根据以下信息，为学生编写一份结构清晰的知识点讲解文档(Markdown格式)。

知识点：{name}
学科分类：{grade} · {topic}
难度：{difficulty}
认知动作：{cognitive}
一句话描述：{desc}
配套工具：{filename}（一个可交互操作的可视化网页）

要求：
1. 直接输出 Markdown 正文，不要寒暄、不要用代码块包裹整篇内容，也不要重复输出一级标题。
2. 文档包含以下五个部分，每部分内容充实但总字数控制在 500~700 字：
   ## 一句话理解
   ## 核心概念（这个知识点讲什么，用通俗语言解释）
   ## 原理与公式（关键定义/定理/公式，公式用文字或简单符号表达即可）
   ## 动手实验（如何操作配套的可视化网页来观察和理解它，至少写3步操作建议）
   ## 学习要点（易错点、记忆口诀或与其他知识的联系，2~4条）
3. 内容必须科学准确，围绕"{name}"展开，不要编造与该知识点无关的内容。
'''


# ============================================================
# 三个按钮对应的后端处理函数
# ============================================================
def list_html_files():
    '''扫描 math 目录，返回全部 HTML 文件名（供下拉框选择）'''
    files = [os.path.basename(p) for p in glob.glob(os.path.join(MATH_DIR, '*.html'))]
    return sorted(files)


def read_html_file(filename):
    '''按钮①：读取并展示 HTML 文件原始内容'''
    if not filename:
        return '', '⚠️ 请先在上方选择一个 HTML 文件'
    path = os.path.join(MATH_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    size_kb = os.path.getsize(path) / 1024
    return content, f'✅ 已读取「{filename}」，原始大小 {size_kb:.1f} KB，共 {len(content)} 字符'


def parse_html_meta(filepath):
    '''读取一个 HTML 文件，提取知识点元数据'''
    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    title = soup.title.string.strip() if soup.title else os.path.basename(filepath)
    name = title.split('·')[0].strip()

    meta = {}
    for tag in soup.find_all('meta'):
        key = tag.get('name')
        if key:
            meta[key] = tag.get('content', '').strip()

    # 页面上的可见文字（去掉脚本和标签）
    for tag in soup(['script', 'style']):
        tag.decompose()
    visible = [ln.strip() for ln in soup.get_text('\n').split('\n') if ln.strip()]

    return {
        'name': name,
        'grade': meta.get('grade', ''),
        'topic': meta.get('topic', ''),
        'difficulty': meta.get('difficulty', ''),
        'priority': meta.get('priority', ''),
        'cognitive': meta.get('cognitive', ''),
        'desc': meta.get('desc', ''),
        'filename': os.path.basename(filepath),
    }, visible


def extract_content(filename):
    '''按钮②：从 HTML 中提取生成知识点所需的关键内容（元数据 + 页面文字）'''
    if not filename:
        return '', '⚠️ 请先在上方选择一个 HTML 文件'
    item, visible = parse_html_meta(os.path.join(MATH_DIR, filename))

    text = (
        f'知识点名称：{item["name"]}\n'
        f'适用学段  ：{item["grade"]}\n'
        f'学科分类  ：{item["topic"]}\n'
        f'难    度  ：{item["difficulty"]}\n'
        f'优 先 级  ：{item["priority"]}\n'
        f'认知动作  ：{item["cognitive"]}\n'
        f'一句话描述：{item["desc"]}\n'
        f'源 文 件  ：{item["filename"]}\n'
        f'\n----- 页面可见文字（{len(visible)} 行）-----\n'
        + '\n'.join(visible)
    )
    return text, f'✅ 已从「{filename}」提取元数据与页面文字，下一步可点击按钮③生成知识点'


def generate_knowledge(filename):
    '''按钮③：调用付费大模型生成知识点 Markdown，并保存到 knowledge_docs 目录'''
    if not filename:
        return '', '⚠️ 请先在上方选择一个 HTML 文件'
    item, _ = parse_html_meta(os.path.join(MATH_DIR, filename))

    # 调用付费模型（失败自动重试 3 次）
    body = None
    for attempt in range(3):
        try:
            resp = llm.invoke([{'role': 'user', 'content': DOC_PROMPT.format(**item)}])
            body = resp.content.strip()
            # 去掉模型偶尔重复输出的一级标题（表头里已经有标题）
            body = '\n'.join(ln for ln in body.splitlines()
                             if not ln.lstrip().startswith('# ')).strip()
            if len(body) >= 150:
                break
        except Exception as e:
            print(f'第{attempt+1}次调用失败: {type(e).__name__}: {e}')
        body = None
        time.sleep(2)

    if body is None:
        return '', '❌ 生成失败：付费 API 多次调用未成功，请检查网络或 Key 后重试'

    md = (
        f'# {item["name"]}\n\n'
        f'> **{item["grade"]} · {item["topic"]}** ｜ '
        f'难度：{item["difficulty"]} ｜ 优先级：{item["priority"]} ｜ '
        f'认知动作：{item["cognitive"]}\n'
        f'> 配套可视化工具：`{item["filename"]}`\n\n'
        f'---\n\n'
        f'{body}\n'
    )

    # 保存为 .md 文件
    out_path = os.path.join(OUT_DIR, filename.replace('.html', '.md'))
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(md)

    status = f'🎉 知识点文档已生成并保存：\n{out_path}\n（共 {len(md)} 字符）'
    return md, status


def refresh_file_list():
    '''刷新下拉框（文件有增减时点）'''
    files = list_html_files()
    value = files[0] if files else None
    return gr.update(choices=files, value=value), f'🔄 已刷新，共发现 {len(files)} 个 HTML 文件'


# ============================================================
# 标签页 UI（由 server.py 在 gr.Tabs() 上下文中调用）
# ============================================================
def create_tab():
    '''构建「知识点扩充」标签页，返回 gr.Tab 对象'''
    with gr.Tab('📚 知识点扩充') as tab:
        gr.Markdown(
            '从 `txt/math` 的可视化 HTML 页面自动生成知识点文档（商汤 SenseNova 付费模型）。'
            '操作顺序：**① 读取 → ② 提取 → ③ 生成**'
        )

        # ---- 文件选择区 ----
        with gr.Row():
            file_dropdown = gr.Dropdown(
                choices=list_html_files(),
                value=list_html_files()[0] if list_html_files() else None,
                label='选择一个可视化 HTML 页面',
                scale=5,
            )
            refresh_btn = gr.Button('🔄 刷新文件列表', scale=1)

        # ---- 三个功能按钮 ----
        with gr.Row():
            btn_read = gr.Button('① 读取 HTML 文件', variant='secondary')
            btn_extract = gr.Button('② 提取关键内容', variant='secondary')
            btn_generate = gr.Button('③ 生成知识点文档', variant='primary')

        status_box = gr.Textbox(label='运行状态', interactive=False, lines=2)

        # ---- 三个结果展示区（用子选项卡切换）----
        with gr.Tabs():
            with gr.Tab('① HTML 原始内容'):
                html_view = gr.Code(language='html', label='HTML 源码', lines=18, interactive=False)
            with gr.Tab('② 提取的关键内容'):
                meta_view = gr.Code(language='markdown', label='元数据 + 页面可见文字',
                                    lines=18, interactive=False)
            with gr.Tab('③ 生成的知识点文档'):
                doc_view = gr.Markdown(label='知识点 Markdown（已保存到 knowledge_docs 目录）')

        # ---- 事件绑定 ----
        refresh_btn.click(refresh_file_list, outputs=[file_dropdown, status_box])
        btn_read.click(read_html_file, inputs=[file_dropdown],
                       outputs=[html_view, status_box])
        btn_extract.click(extract_content, inputs=[file_dropdown],
                          outputs=[meta_view, status_box])
        btn_generate.click(generate_knowledge, inputs=[file_dropdown],
                           outputs=[doc_view, status_box])

    return tab
