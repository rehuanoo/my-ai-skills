# -*- coding: utf-8 -*-
"""
AI 智能编辑 —— 后端服务
========================
为前端 (02-ai-editor-fullstack/AI_editor，Vue3 + Ant Design Vue) 提供 Markdown 润色接口。

流程：
    前端「✨ AI 润色」按钮 → POST /polish {text: markdown}
    → 商汤 SenseNova 付费模型润色（借鉴 01-llm-knowledge-workspace/component/tab1.py 的调用方式）
    → 返回 {text: 润色后的 markdown}

启动方式（复用 15-transformers-basics 的虚拟环境，里面有 fastapi/uvicorn/langchain）：
    .\.venv\Scripts\Activate.ps1      # 先激活你自己的虚拟环境
    cd Ai_editor_server
    python server.py
启动后：先运行本服务，再启动前端 npm run dev，页面右上角即可使用 AI 润色。
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

import socket
import uvicorn

# ============================================================
# 付费大模型（商汤 SenseNova，OpenAI 兼容协议）—— 与 tab1.py 相同配置
# ============================================================
llm = ChatOpenAI(
    model='sensenova-6.8-flash-lite',
    base_url='https://token.sensenova.cn/v1',
    api_key=os.getenv("SENSENOVA_API_KEY", ""),
    temperature=0.4,   # 润色任务温度不宜过高，保持原文风格稳定
    timeout=120,
)

# 润色提示词：只改文字表达，不动 Markdown 结构
POLISH_PROMPT = '''你是资深文字编辑。请润色下面这篇 Markdown 文档。

要求：
1. 严格保持 Markdown 结构不变：标题层级、列表、表格、代码块、引用、链接等一律原样保留。
2. 只优化文字表达：语句更通顺、用词更准确、修正错别字和语病。
3. 不改变原意、不删减内容、不新增内容。
4. 直接输出润色后的 Markdown 正文，不要任何解释或寒暄，也不要用代码块包裹整篇内容。

----- 待润色的 Markdown 文档 -----
{text}
----- 文档结束 -----
'''

app = FastAPI(title='AI 智能编辑后端')

# 跨域：Vue dev server 跑在 localhost:5173，必须放行，否则浏览器拦截请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],        # 本地学习工具，放开即可；上线要改成具体域名
    allow_methods=['*'],
    allow_headers=['*'],
)


class PolishRequest(BaseModel):
    '''请求体：{ "text": "markdown 原文" }'''
    text: str


@app.post('/polish')
def polish(req: PolishRequest):
    '''润色接口：接收 Markdown 文本，返回商汤模型润色后的 Markdown'''
    if not req.text.strip():
        raise HTTPException(status_code=400, detail='内容为空，请先输入或载入 Markdown')

    # 调用付费模型（失败自动重试 3 次，借鉴 tab1.py 的写法）
    result = None
    last_err = None
    for attempt in range(3):
        try:
            resp = llm.invoke([{'role': 'user',
                                'content': POLISH_PROMPT.format(text=req.text)}])
            result = resp.content.strip()
            if result:
                break
        except Exception as e:
            last_err = e
            print(f'第 {attempt + 1} 次润色失败: {type(e).__name__}: {e}')

    if not result:
        raise HTTPException(status_code=502,
                            detail=f'润色失败：付费 API 多次调用未成功（{last_err}）')

    return {'text': result}


@app.get('/health')
def health():
    '''健康检查：浏览器打开 http://127.0.0.1:8000/health 看服务是否在跑'''
    return {'status': 'ok'}


def port_in_use(host, port):
    '''检测端口是否已被占用（比如已经有一个 server.py 在运行）'''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


if __name__ == '__main__':
    HOST, PORT = '127.0.0.1', 8000

    if port_in_use(HOST, PORT):
        print(f'⚠️ 端口 {PORT} 已被占用：后端服务可能已经在运行了。')
        print(f'   如需重启，请先在原来运行 server.py 的窗口按 Ctrl+C 结束旧服务。')
        raise SystemExit(0)

    print('⏳ 正在启动 AI 智能编辑后端……', flush=True)
    print(f'✅ 润色接口：POST http://{HOST}:{PORT}/polish（供前端调用）', flush=True)
    uvicorn.run(app, host=HOST, port=PORT)
