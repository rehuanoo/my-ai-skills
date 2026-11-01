# -*- coding: utf-8 -*-
"""
Tab 3：思维导图生成
==================
输入一个主题 → 商汤 SenseNova 付费模型生成 Markmap 风格的 Markdown →
前端用 markmap 渲染成思维导图。

前端渲染借鉴 11.svelte/learn_svelte/src/App.svelte 里 markmap 的用法：
    Transformer.transform(markdown) → root 节点树
    Markmap.create(svg, options, root) → 画到 SVG
Gradio 页面不是 npm 工程，无法 import 'markmap-view'，改用 markmap 官方
文档推荐的 CDN 全局变量形式（window.markmap.Transformer / Markmap），
相关 <script> 由 server.py 在 demo.launch(head=MARKMAP_HEAD) 注入页面。

对外暴露：
    create_tab()  —— 由 server.py 挂载到 gr.Tabs()
    MARKMAP_HEAD  —— 由 server.py 在 launch() 时注入页面 <head>
"""

import re
import time

import gradio as gr

from component.tab1 import llm   # 复用商汤 SenseNova 付费模型

# ============================================================
# 页面 <head> 注入的 markmap 脚本（顺序不能变：d3 → view → lib）
# 三者的 UMD 全局变量都挂在 window.markmap 上，后加载的合并属性
# ============================================================
MARKMAP_HEAD = '''
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18.12"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.18.12"></script>
'''

# 前端渲染回调（纯 js 事件，不经过后端队列）：
# md_view 的内容一变化（模型生成完成 / 手动编辑）就重画 SVG
RENDER_JS = """(md) => {
    const svg = document.getElementById('tab3-markmap-svg');
    if (!svg) return;
    if (!md || !md.trim()) {
        window.__tab3MM = undefined;
        svg.innerHTML = '';
        return;
    }
    if (!window.markmap || !window.markmap.Transformer) {
        svg.innerHTML = '<text x="20" y="40" fill="#c00" font-size="16">'
            + 'markmap 脚本（CDN）加载失败，请检查网络后刷新页面</text>';
        return;
    }
    try {
        const { root } = window.markmap.Transformer.transform(md);
        if (!window.__tab3MM) {
            // 首次渲染
            window.__tab3MM = window.markmap.Markmap.create(svg, undefined, root);
        } else {
            // 后续更新：替换数据并自适应缩放
            window.__tab3MM.setData(root);
            window.__tab3MM.fit();
        }
    } catch (err) {
        console.error('[思维导图] 渲染失败:', err);
    }
}"""

# 生成思维导图 Markdown 的提示词
MINDMAP_PROMPT = '''你是思维导图设计专家。请围绕主题《{theme}》编写一份 Markmap 思维导图用的 Markdown 大纲。

要求：
1. 只输出 Markdown 大纲本身，不要任何解释、寒暄，也不要用代码块包裹。
2. 层级结构：
   - 一级标题（# ）只有一个，即主题本身（可适当润色）；
   - 用二级标题（## ）划分 4~8 个核心分支；
   - 每个分支下用无序列表（- 与空格缩进）展开 2~5 层要点，每条尽量精炼（不超过 25 字）。
3. 内容科学准确、逻辑清晰，覆盖主题的主要方面；不要输出表格、图片或代码。
4. 若主题过于宽泛，选择最有价值、最常见的学习或应用角度展开。
'''


def _extract_markdown(text):
    '''剥掉模型偶尔套上的 ```markdown ...``` 围栏'''
    m = re.search(r'```(?:markdown|md)?\s*\n(.*?)```', text, re.S)
    return (m.group(1) if m else text).strip()


def generate_markmap(theme):
    '''调用付费模型生成 Markmap 格式的 Markdown（失败/结构不符自动重试 3 次）'''
    theme = (theme or '').strip()
    if not theme:
        return '', '⚠️ 请先在上方输入导图主题'

    md = None
    for attempt in range(3):
        try:
            resp = llm.invoke([{'role': 'user', 'content': MINDMAP_PROMPT.format(theme=theme)}])
            out = _extract_markdown(resp.content.strip())
            # 基本结构校验：一级标题开头，且至少有 2 个二级分支
            if out.startswith('#') and len(re.findall(r'^##\s+\S', out, re.M)) >= 2:
                md = out
                break
            print(f'[思维导图] 第{attempt+1}次输出不符合大纲结构，重试')
        except Exception as e:
            print(f'[思维导图] 第{attempt+1}次调用失败: {type(e).__name__}: {e}')
        time.sleep(2)

    if md is None:
        return '', '❌ 生成失败：付费 API 多次调用未成功，请检查网络或 Key 后重试'
    return md, f'✅ 思维导图已生成（{len(md)} 字符），已在下方渲染；也可直接编辑 Markdown 后自动重画'


# ============================================================
# 标签页 UI（由 server.py 在 gr.Tabs() 上下文中调用）
# ============================================================
def create_tab():
    '''构建「思维导图」标签页，返回 gr.Tab 对象'''
    with gr.Tab('🧠 思维导图') as tab:
        gr.Markdown(
            '输入一个主题 → 付费模型生成 Markmap 格式的 Markdown → '
            '用 markmap 渲染成思维导图（用法借鉴 `11.svelte` 项目，CDN 引入）。'
        )

        with gr.Row():
            theme_box = gr.Textbox(
                label='导图主题',
                placeholder='例如：如何学好英语 / 卷积神经网络 / 二次函数',
                lines=1, scale=5,
            )
            btn_generate = gr.Button('生成思维导图', variant='primary', scale=1)

        status_box = gr.Textbox(label='运行状态', interactive=False, lines=2)

        md_view = gr.Code(
            label='Markmap Markdown（模型生成后可直接手动修改，改完自动重画）',
            value='', language='markdown', lines=12, interactive=True,
        )

        gr.HTML(
            '<svg id="tab3-markmap-svg" style="width:100%;height:560px;'
            'background:#fff;border:1px solid #e5e4e7;border-radius:8px"></svg>'
        )

        # ---- 事件绑定 ----
        # api_name：前端（如 11.svelte 的 @gradio/client）调用时用的接口名 /generate_markmap
        btn_generate.click(generate_markmap, inputs=[theme_box],
                           outputs=[md_view, status_box],
                           api_name='generate_markmap')
        # 纯前端渲染：Markdown 内容一变就重画（fn=None，不占用后端队列）
        md_view.change(fn=None, inputs=[md_view], js=RENDER_JS)

    return tab
