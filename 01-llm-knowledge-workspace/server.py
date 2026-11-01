# -*- coding: utf-8 -*-
"""
AI 学习工作台 —— Gradio 应用主入口
==================================
本文件只负责搭建页面框架并挂载各功能标签页，
具体功能分别在 component/ 目录下的独立模块中实现：

    component/tab1.py  —— 📚 知识点扩充（读取 HTML → 提取内容 → 付费模型生成知识点）
    component/tab2.py  —— 📝 论文生成（大纲 → 章节 → 文献论点提取与筛选）
    component/tab3.py  —— 🧠 思维导图（付费模型生成 Markmap Markdown → markmap 渲染）
    component/tab4.py  —— ✍️ AI 写作助手（续写 / 润色 / 生成标题，供 Vue 前端调用 API）

新增功能时：
    1. 在 component/ 下新建 tabN.py，实现 create_tab()
    2. 在下方 import 并在 gr.Tabs() 中调用即可，无需改动已有代码

启动方式（激活已有虚拟环境后运行，无需重新安装依赖）：
    .\.venv\Scripts\Activate.ps1      # 先激活你自己的虚拟环境
    python server.py
启动后浏览器打开 http://127.0.0.1:7860
"""

import socket

import gradio as gr

# 导入各标签页的构建函数（component 是与本文件同级的 Python 包）
from component.tab1 import create_tab as create_tab1
from component.tab2 import create_tab as create_tab2
from component.tab3 import create_tab as create_tab3, MARKMAP_HEAD
from component.tab4 import create_tab as create_tab4
import sqlite3




# ============================================================
# 页面框架：一个 Blocks + 一个 Tabs，所有标签页同页显示
# ============================================================
with gr.Blocks(title='AI 学习工作台') as demo:
    gr.Markdown('# 🎓 AI 学习工作台')

    with gr.Tabs():
        create_tab1()   # 📚 知识点扩充
        create_tab2()   # 📝 论文生成
        create_tab3()   # 🧠 思维导图
        create_tab4()   # ✍️ AI 写作助手


def port_in_use(host, port):
    '''检测端口是否已被占用（比如已经有一个 server.py 在运行）'''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def auth(username, password):
    conn = sqlite3.connect('./db/database.db') # 连接数据库
    # 创建cursor对象，用于执行SQL语句
    cursor = conn.cursor()
    # 查询user表，判断账号密码是否正确
    cursor.execute("SELECT * FROM user WHERE username = ? AND password = ?", (username, password))
    # 将查询提交
    result = cursor.fetchone()
    # 关闭cursor和连接
    cursor.close()
    #  关闭连接
    conn.close()
    # 判断results是否有数据
    if result:
        return True
    else:
        return False

    


    # return username == 'admin' and password == '123456'


if __name__ == '__main__':
    HOST, PORT = '127.0.0.1', 7860

    # 端口已被占用时给出明确提示，而不是僵在报错信息里
    if port_in_use(HOST, PORT):
        print(f'⚠️ 端口 {PORT} 已被占用：服务可能已经在运行了。')
        print(f'   请直接用浏览器打开 http://{HOST}:{PORT} ；')
        print(f'   如需重启，请先在原来运行 server.py 的窗口按 Ctrl+C 结束旧服务。')
        raise SystemExit(0)

    # launch() 会持续阻塞——这是 Web 服务器的正常行为，不是卡死
    print('⏳ 正在启动 AI 学习工作台（加载依赖约需 10~20 秒，请稍候）……', flush=True)
    print(f'✅ 启动成功后：浏览器访问 http://{HOST}:{PORT} ；停止服务请在本窗口按 Ctrl+C', flush=True)
    demo.launch(server_name=HOST,
                server_port=PORT,
                inbrowser=True,
                theme=gr.themes.Soft(),
                auth=auth,
                max_threads=4,
                show_error=True,
                head=MARKMAP_HEAD)   # tab3 思维导图需要的 markmap CDN 脚本
# inbrowser=True  # 自动打开浏览器
# auth=('admin', '123456')  # 登录密码
# server_port=7860  # 端口号
# server_name=HOST  # 服务器地址
# max_threads=4  # 最大线程数(同时多少人能用)
# show_error=True  # 显示错误信息
# favicon_path='favicon.ico'  # 网页图标

