# -*- coding: utf-8 -*-
"""
Tab 4：✍️ AI 写作助手
========================
三个功能（均为商汤 SenseNova 付费模型，复用 tab1 的 llm 配置）：

    ✍️ 续写  —— 根据文档现有内容续写后续内容（API: /continue_markdown）
    ✨ 润色  —— 优化文字表达，保持 Markdown 结构（API: /polish_markdown）
    📌 标题  —— 根据内容生成 5 个备选标题（API: /gen_titles）

除了本页面的 UI 按钮，这三个接口同时供 02-ai-editor-fullstack/AI_editor 前端
（Vue3 + @gradio/client）远程调用：
    result = await client.predict('/continue_markdown', { text: '...' })

对外只暴露 create_tab()，由 server.py 挂载到主页面。
"""

import time

import gradio as gr

from component.tab1 import llm   # 复用商汤 SenseNova 模型配置（OpenAI 兼容协议）

# ============================================================
# 提示词
# ============================================================
CONTINUE_PROMPT = '''你是写作助手。请根据下面 Markdown 文档的现有内容，续写后续内容。

要求：
1. 风格、语气与格式和原文保持一致（Markdown 语法）。
2. 只输出续写的部分，不要重复原文，不要任何解释。
3. 续写 150~300 字，自然承接原文结尾。

----- 文档现有内容 -----
{text}
----- 文档结束 -----
'''

POLISH_PROMPT = '''你是资深文字编辑。请润色下面这篇 Markdown 文档。

要求：
1. 严格保持 Markdown 结构不变：标题层级、列表、表格、代码块、引用、链接一律原样保留。
2. 只优化文字表达：语句更通顺、用词更准确、修正错别字和语病。
3. 不改变原意、不删减内容、不新增内容。
4. 直接输出润色后的 Markdown 全文，不要任何解释，也不要用代码块包裹。

----- 文档 -----
{text}
----- 文档结束 -----
'''

TITLES_PROMPT = '''你是标题专家。请根据下面的 Markdown 文档内容，生成 5 个适合它的标题。

要求：
1. 每个标题不超过 20 字，概括文档主旨。
2. 风格吸引人但不夸张，符合原文内容。
3. 只输出 5 行，每行一个标题，不要编号、不要解释。

----- 文档 -----
{text}
----- 文档结束 -----
'''


# ============================================================
# 通用调用封装（失败重试 3 次，借鉴 tab1.py 的写法）
# ============================================================
def _invoke_with_retry(prompt, retries=3):
    '''调用付费模型，返回去掉首尾空白后的文本；多次失败则抛出异常'''
    last_err = None
    for attempt in range(retries):
        try:
            resp = llm.invoke([{'role': 'user', 'content': prompt}])
            body = resp.content.strip()
            # 防止模型偶尔输出空内容
            if len(body) >= 2:
                return body
        except Exception as e:
            last_err = e
            print(f'第{attempt + 1}次调用失败: {type(e).__name__}: {e}')
        time.sleep(2)
    raise RuntimeError(f'付费 API 多次调用未成功：{last_err}')


def _check(text):
    '''空内容检查（UI 和 API 共用）'''
    if not text or not text.strip():
        raise ValueError('内容为空，请先输入或载入 Markdown 文档')


# ============================================================
# 三个按钮对应的后端处理函数
# ============================================================
def continue_md(text):
    '''✍️ 续写：返回续写的 Markdown 片段（不含原文）'''
    _check(text)
    return _invoke_with_retry(CONTINUE_PROMPT.format(text=text))


def polish_md(text):
    '''✨ 润色：返回润色后的 Markdown 全文'''
    _check(text)
    return _invoke_with_retry(POLISH_PROMPT.format(text=text))


def gen_titles(text):
    '''📌 标题：返回 5 个标题的列表（gr.JSON 输出，前端拿到的是数组）'''
    _check(text)
    body = _invoke_with_retry(TITLES_PROMPT.format(text=text))
    titles = [ln.strip().lstrip('0123456789.、) ')
              for ln in body.splitlines() if ln.strip()]
    if len(titles) < 5:
        raise RuntimeError(f'模型只生成了 {len(titles)} 个标题，请重试')
    return titles[:5]


# ============================================================
# 标签页 UI（由 server.py 在 gr.Tabs() 上下文中调用）
# ============================================================
def create_tab():
    '''构建「AI 写作助手」标签页，返回 gr.Tab 对象'''
    with gr.Tab('✍️ AI 写作助手') as tab:
        gr.Markdown(
            '输入 Markdown 内容 → **续写 / 润色 / 生成标题**（商汤付费模型）。'
            '这三个接口同时供 `02-ai-editor-fullstack` 的 Vue 前端通过 API 调用。'
        )

        content_box = gr.Textbox(lines=12, label='文档内容（Markdown）',
                                 placeholder='在此粘贴或输入 Markdown 文档……')

        with gr.Row():
            btn_cont = gr.Button('✍️ 续写', variant='secondary')
            btn_polish = gr.Button('✨ 润色', variant='primary')
            btn_titles = gr.Button('📌 生成 5 个标题', variant='secondary')

        with gr.Tabs():
            with gr.Tab('续写结果'):
                cont_view = gr.Markdown(label='续写的内容（会追加到原文结尾）')
            with gr.Tab('润色结果'):
                polish_view = gr.Code(language='markdown', label='润色后的全文', lines=12)
            with gr.Tab('标题'):
                titles_view = gr.JSON(label='5 个备选标题')

        # ---- 事件绑定（api_name：前端 @gradio/client 调用时用的接口名）----
        btn_cont.click(continue_md, inputs=[content_box],
                       outputs=[cont_view], api_name='continue_markdown')
        btn_polish.click(polish_md, inputs=[content_box],
                         outputs=[polish_view], api_name='polish_markdown')
        btn_titles.click(gen_titles, inputs=[content_box],
                         outputs=[titles_view], api_name='gen_titles')

    return tab
