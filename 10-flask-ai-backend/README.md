# 10 · Flask AI 后端进阶（10 个专题）

> 从「Hello World 路由」一路做到「流式输出的 AI 聊天后端」，前端同步手写一遍。

## 技术栈

`Flask` · `Jinja2 模板` · `flask-cors` · 智谱 GLM（`zai` SDK，流式）· `SQLite` · `fetch` / SSE 流式 · `cookie` / `session`

## 专题清单

| 目录 | 内容 |
|------|------|
| `01.Flask` | 路由、模板渲染、请求参数、静态文件 |
| `03.Ai_api` | 大模型 API 封装：普通返回 + **流式返回**（`Response` + `stream_with_context`） |
| `04.讯飞ai聊天交互` | 手写前端聊天界面（HTML/CSS/JS）调用后端 |
| `05.fetch` | 前端用 `fetch` 消费普通 JSON 与流式响应 |
| `06.讯飞ai聊天交互` | 聊天界面迭代版：历史消息、状态处理 |
| `07.静态文件与cookie` | `static` / `templates` 的目录约定与 `cookie` 读写 |
| `08.cookie-session` | 登录态：cookie 与加密 session 的差别、`secret_key` 的作用 |
| `09.文件上传` | `multipart/form-data` 接收、校验、落盘、回显 |
| `10.sqlite` | 建表 SQL 与 Python 侧增删改查 |
| `13.flaskSql` | 完整的用户注册 / 登录 / 列表 / 编辑（模板渲染版 CRUD） |

## 运行

```powershell
pip install -r requirements.txt

# 选一个专题跑，例如流式 AI 接口
cd 03.Ai_api
$env:ZHIPU_API_KEY = "你的智谱 Key"
python server.py            # http://127.0.0.1:5000

# 完整用户系统
cd 13.flaskSql
python server.py
```

## 实现要点

- **流式输出**：`client.chat.completions.create(stream=True)` + `Response(generate(), mimetype='text/event-stream')`，前端边收边渲染，而不是等完整结果。
- **推理过程可见**：同时读取 `delta.reasoning_content` 与 `delta.content`，把「思考过程」和「正式回答」分开输出。
- **CORS**：前后端分离调试时跨域是必踩的坑，这里配置了 `flask-cors`。
- **安全**：数据库查询用参数化，登录态用 session；`secret_key` 改为环境变量读取，不再硬编码。
