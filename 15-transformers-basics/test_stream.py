"""
Qwen3-0.6B 流式推理脚本
- 在 GPU 上运行（CUDA）
- 流式输出（边生成边打印，不用等全部生成完）
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from threading import Thread
from transformers import TextIteratorStreamer

# 模型路径（本地）
model_name = "./models/Qwen3-0.6B"

# 自动选择设备：优先 GPU，没有 GPU 用 CPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"使用设备：{device}")
if device == "cuda":
    print(f"GPU 型号：{torch.cuda.get_device_name(0)}")
    print(f"显存总量：{torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

# 1. 加载 tokenizer
print("正在加载 tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 2. 加载模型到 GPU
#    - torch_dtype=torch.float16：半精度，显存占用减半，速度更快
#    - device_map="auto"：自动放到 GPU 上
print("正在加载模型...")
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    dtype=torch.float16,           # 半精度，显存占用减半，速度更快
    device_map="auto",             # 自动放到 GPU 上
)
model.eval()
print(f"模型已加载到：{next(model.parameters()).device}")

# 3. 准备输入
prompt = "介绍3道川菜"
messages = [
    {"role": "user", "content": prompt}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

# 4. 创建流式输出器
#    TextIteratorStreamer 会把 generate 的输出实时塞进队列，
#    主线程可以从迭代器里逐个 token 取出，达到"边生成边打印"的效果
streamer = TextIteratorStreamer(
    tokenizer,
    skip_prompt=True,        # 不打印输入 prompt
    skip_special_tokens=True # 不打印 <eos> 等特殊 token
)

# 5. 配置 generate 参数（关键：把 streamer 传进去）
generation_kwargs = dict(
    **model_inputs,
    max_new_tokens=1024,      # 输出最大长度，按需调
    do_sample=True,           # 采样生成（更自然）
    temperature=0.7,          # 控制随机性，越大越多样
    top_p=0.8,                # 核采样
    repetition_penalty=1.05,  # 重复惩罚，防止复读
    streamer=streamer,
)

# 6. 用子线程跑 generate，主线程同时从 streamer 取 token 打印
print("\n" + "=" * 60)
print("开始生成（流式输出）：")
print("=" * 60)
print()
print("AI：", end="", flush=True)

thread = Thread(target=model.generate, kwargs=generation_kwargs)
thread.start()

# 主线程：边取边打印
for token_text in streamer:
    print(token_text, end="", flush=True)

# 等子线程完全结束
thread.join()

print("\n")
print("=" * 60)
print("生成完毕")
