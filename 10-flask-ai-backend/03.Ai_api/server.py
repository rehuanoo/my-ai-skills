# 智谱AI调用
import os
from zai import ZhipuAiClient
from flask import Flask, request, render_template,Response,stream_with_context
from flask_cors import CORS
#设置跨域
app = Flask(__name__)
CORS(app)
# 初始化客户端
client = ZhipuAiClient(api_key=os.getenv("ZHIPU_API_KEY", ""))

@app.route('/')
def index():
  return "Hello, World!"

@app.route('/api/chat', methods=['GET'])
def chat():
  chat = request.args.get('chat')
  print(chat)
  messages=[{
    "role": "user",
    "content": chat
  }]
  def invoke_fn():
    resContent = ''
    # if len(messages) > 0:
    #     query = input("请继续输入你想提问的内容: ")
    # else:
    #     query = input("请输入你想提问的内容: ")
    # messages.append({"role": "user", "content": chat})
    response = client.chat.completions.create(
        model="glm-5",
        messages=messages,
        temperature=0.6,
        stream=True, # 添加这个就可以让结果流式输出
    )
    # 实时获取回复
    for chunk in response:
        # 保险判断（判断是否有chunk.choices）
        if not chunk.choices:
            continue

        # 获取内容
        delta = chunk.choices[0].delta

        # 推理过程（如果有就打印）
        if delta.reasoning_content:
            print(delta.reasoning_content, end="", flush=True)
            resContent += delta.reasoning_content

        # 正常回答内容
        if delta.content:
            print(delta.content, end="", flush=True)
            resContent += delta.content

        # 判断是否结束
        if chunk.choices[0].finish_reason is not None:
            print("\n\n****内容已经完结*****")
            print("结束原因:", chunk.choices[0].finish_reason)
            print("\n\n****继续提问*****")
            # 问题回答完继续提问
            # sse_invoke_fn()
            
    return resContent
    
  resultContent = invoke_fn()
  print(resultContent)
  return resultContent

@app.route('/chat', methods=['GET'])
def chatPage():
  return render_template('chat.html')


# 定义流式聊天页面的路由
@app.route('/chatstream',methods=['GET'])
def chatStreamPage():
    return render_template('chat_stream.html')

# 定义流式聊天接口的路由
@app.route('/api/chat_stream',methods=['GET'])
def chat_stream():
    # 获取前端传递的参数
    chat = request.args.get('chat')
    print(chat)
    messages = [{"role": "user", "content": chat}]

    def sse_invoke_fn():
        # 创建聊天完成请求
        response = client.chat.completions.create(
            model="glm-5",
            messages=messages,
            temperature=0.6,
            stream=True, # 添加这个就可以让结果流式输出
        )
        # 实时获取回复
        for chunk in response:
            # 保险判断（判断是否有chunk.choices）
            if not chunk.choices:
                continue

            # 获取内容
            delta = chunk.choices[0].delta

            # 推理过程（如果有就打印）
            if delta.reasoning_content:
                print(delta.reasoning_content, end="", flush=True)
                # yield可以先输出内容，然后继续执行循环，这个输出的内容会被sse返回给前端
                # yield "data: %s\n\n" % delta.reasoning_content

            # 正常回答内容
            if delta.content:
                print(delta.content, end="", flush=True)
                yield "data: %s\n\n" % delta.content

            # 判断是否结束
            if chunk.choices[0].finish_reason is not None:
                print("\n\n****内容已经完结*****")
                print("结束原因:", chunk.choices[0].finish_reason)
                if(chunk.choices[0].finish_reason == "stop"):
                    yield "data: !!!finish!!!\n\n"
                else:
                    yield "data: !!!error!!!\n\n"
                break

        return 
    
    # stream_with_context这个会自动处理sse，将yield的内容转持续输出给前端
    resultContent = Response(stream_with_context(sse_invoke_fn()), content_type="text/event-stream")
    return resultContent



if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080, debug=True)


